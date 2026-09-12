import src.copywriter as cw

def test_parse_llm_json_clean():
    out = cw._parse_llm_json('{"title":"T","desc":"D","tags":["a","b"]}')
    assert out == {"title": "T", "desc": "D", "tags": ["a", "b"]}

def test_parse_llm_json_with_fenced_code():
    raw = '好的，这是结果：\n```json\n{"title":"T2","desc":"D2","tags":["x"]}\n```'
    out = cw._parse_llm_json(raw)
    assert out["title"] == "T2"

def test_parse_llm_json_garbage_returns_none():
    assert cw._parse_llm_json("我不是JSON") is None

def test_fallback_template():
    meta = {"keyword": "ocean waves", "author": "Cameraman", "duration": 120}
    out = cw.fallback_copywriting(meta)
    assert isinstance(out["tags"], list) and out["title"]
    assert "来源" in out["desc"]  # 声明由入口统一拼接，fallback 不再自带
