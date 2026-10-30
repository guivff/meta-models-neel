from projects.g_agreement.understand.q1.prepare import quotas


def test_all_tier_sizes_balanced_and_cover_every_row():
    for n in [9,12,4]:
        fs=[f'feature{i}' for i in range(n)];q=quotas(fs,'tier')
        assert set(q)==set(fs)
        assert all(sum(v.values())>=1 for v in q.values())
        assert sum(v['A'] for v in q.values())==sum(v['B'] for v in q.values())==10
        assert max(sum(v.values()) for v in q.values())-min(sum(v.values()) for v in q.values())<=1
        assert all(abs(v['A']-v['B'])<=1 for v in q.values())
        assert q==quotas(list(reversed(fs)),'tier')
