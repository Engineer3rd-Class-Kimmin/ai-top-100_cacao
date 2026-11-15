# 공개 코드 검증 기록

2026-11-15 · Python 3.11.9 · Windows · ai-assisted

명령(저장소 루트, ai_coach의 PYTHONPATH는 PowerShell에서 `$env:PYTHONPATH`로 설정):

```text
python -m unittest discover -s tests -v
```

실제 관측: **Ran 12 tests; OK**.

대회 후 공개용으로 추가한 합성 어댑터 계약. 당시 245개 운영 회귀·공식 인증·환불 실행과 별개다.

테스트 입력은 해당 테스트 파일에 고정되어 있다. 기대값은 변경하지 않았다.

| 검토한 코드·입력 | SHA-256 |
|---|---|
| `examples/request_adapter.py` | `895081c11d42022ed2792782cfbaaa0b83f1ae47e99cb9b1336eca4e08f7cacb` |
| `tests/test_request_contract.py` | `10d8025fb2244131d4b70e0b65835f967811976c54ec10de5151cb92ee3535ae` |
