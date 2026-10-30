"""Real CPU backward on tiny 64-layer Qwen; not CUDA/Triton certification."""
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import worker as W


class TinyTokenizer:
    pad_token_id, eos_token_id = 0, 2
    tokens = {'a0': [6, 7], 'b0': [8], 'a1': [9, 10, 11], 'b1': [12, 13]}

    def encode(self, value, add_special_tokens=False):
        return self.tokens[value]


class ProductionTrainingCPU(unittest.TestCase):
    def test_actual_two_steps_all_64_layers_and_frozen_base(self):
        import numpy as np
        import torch
        from transformers import Qwen3_5TextConfig, Qwen3_5ForCausalLM
        torch.set_num_threads(1)
        torch.manual_seed(W.C.SEED)
        config = Qwen3_5TextConfig(vocab_size=40, hidden_size=16, intermediate_size=24,
            num_hidden_layers=64, num_attention_heads=2, num_key_value_heads=1, head_dim=8,
            linear_key_head_dim=4, linear_value_head_dim=4, linear_num_key_heads=1,
            linear_num_value_heads=2, linear_conv_kernel_dim=2,
            layer_types=['linear_attention' if i % 4 != 3 else 'full_attention' for i in range(64)],
            max_position_embeddings=64, pad_token_id=0, bos_token_id=1, eos_token_id=2,
            use_cache=False)
        model = Qwen3_5ForCausalLM(config)
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
        frozen = {n: p.detach().clone() for n, p in model.named_parameters()}
        mapping = W.C.read(W.C.HERE / 'LORA_TARGETS.json')
        mounted, parameters = W.attach_lowrank(model, mapping)
        self.assertTrue(model.is_gradient_checkpointing)
        self.assertEqual({name.split('.')[-1] for name, module in model.named_modules()
                          if hasattr(module, 'A') and hasattr(module, 'B')}, set(mapping['target_modules']))
        originals = [x[2] for x in mounted]
        reader = W.make_reader(model, TinyTokenizer())
        reader._slots[44] = ([1, 3, 4, 5], 1)
        spec = {f: {'olens': [['a0', 'b0'], ['a1', 'b1']]} for f in W.C.CONTENT}
        batch = [{'id': str(i), 'y': i % 2, 'phrasing': (i // 2) % 2, 'feature': W.C.CONTENT[i % 9]} for i in range(8)]
        index = {str(i): i for i in range(8)}
        acts = np.random.default_rng(123).normal(size=(8, 16)).astype('float32')
        optimizer = W.optimizer_for(parameters)
        before_a = [p.detach().clone() for _, _, _, module in mounted for p in module.A]
        before_b = [p.detach().clone() for _, _, _, module in mounted for p in module.B]
        calls = []
        def capture(_model, _args, kwargs):
            calls.append({k: kwargs[k].detach().clone() for k in ('inputs_embeds', 'attention_mask', 'labels')})
        handle = model.register_forward_pre_hook(capture, with_kwargs=True)
        with mock.patch('torch.cuda.synchronize', side_effect=AssertionError('CPU must not synchronize CUDA')):
            first = W.train_step(reader, batch, index, acts, spec, optimizer, diagnostics=True)
            after_a = [p.detach().clone() for _, _, _, module in mounted for p in module.A]
            after_b = [p.detach().clone() for _, _, _, module in mounted for p in module.B]
            second = W.train_step(reader, batch, index, acts, spec, optimizer, diagnostics=True)
        handle.remove()
        for report in (first, second):
            self.assertTrue(report['finite_loss'])
            self.assertTrue(report['finite_gradients'])
            self.assertTrue(report['frozen_parameter_grads_none'])
        self.assertTrue(all(torch.equal(a, b) for a, b in zip(before_a, after_a)))
        self.assertTrue(any(not torch.equal(a, b) for a, b in zip(before_b, after_b)))
        final_a = [p for _, _, _, module in mounted for p in module.A]
        final_b = [p for _, _, _, module in mounted for p in module.B]
        self.assertTrue(any(not torch.equal(a, b) for a, b in zip(after_a, final_a)))
        self.assertTrue(any(not torch.equal(a, b) for a, b in zip(after_b, final_b)))
        self.assertTrue(all(p.grad is not None and torch.isfinite(p.grad).all() for p in parameters))
        self.assertEqual(len(calls), 2)
        actual = calls[0]
        self.assertEqual(tuple(actual['inputs_embeds'].shape), (8, 7, 16))
        for i, item in enumerate(batch):
            tail = reader.tok.encode(spec[item['feature']]['olens'][item['phrasing']][0 if item['y'] else 1])
            self.assertEqual(actual['labels'][i].tolist(), [-100]*4 + tail + [-100]*(3-len(tail)))
            self.assertEqual(actual['attention_mask'][i].tolist(), [1]*(4+len(tail))+[0]*(3-len(tail)))
            expected = torch.tensor(acts[i]) / torch.tensor(acts[i]).norm() * 16000
            torch.testing.assert_close(actual['inputs_embeds'][i, 1], expected)
            torch.testing.assert_close(actual['inputs_embeds'][i, 0], model.get_input_embeddings().weight[1])
        W.detach_lowrank(mounted)
        for n, p in model.named_parameters():
            self.assertFalse(p.requires_grad)
            self.assertIsNone(p.grad)
            self.assertTrue(torch.equal(p, frozen[n]), n)
        self.assertTrue(all(getattr(parent, name) is original for parent, name, original, _ in mounted))
        torch.manual_seed(W.C.SEED)
        reset, _ = W.attach_lowrank(model, mapping)
        self.assertTrue(all(torch.count_nonzero(p) == 0 for _, _, _, module in reset for p in module.B))
        self.assertEqual([x[2] for x in reset], originals)
        W.detach_lowrank(reset)


if __name__ == '__main__':
    unittest.main()
