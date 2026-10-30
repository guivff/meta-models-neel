"""Phase W pod pipeline (PREREG_WV.md, manifest/brief_wv.md): S1 capture, S2 steering matrix, S3 reader scoring (+ V6, S3v1),
S4 consistency null, STATUS writer and the tmux chain ``run_w.sh``. Every stage is a CLI, resumable by key, writes a DONE marker
under results/g_agreement/w/<stage>/ and refuses to redo finished work unless ``--force``."""
