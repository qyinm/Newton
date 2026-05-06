# Task 6 Plan: Link QA planning provenance to execution reports

## Goal

Task 6의 다음 최소 goal은 **`qa plan`으로 생성된 accepted scenario를 기존 `qa run` 실행 결과와 연결하는 것**이다.

즉, Newton이 아직 새로운 intelligent planner나 multi-agent evaluator가 되는 것이 아니라:

1. agent/template이 QA scenario를 생성하고,
2. Newton이 schema validation으로 accepted scenario를 확정하고,
3. 사람이 그 scenario를 `qa run`으로 실행할 때,
4. 실행 report/evidence가 어떤 planning provenance에서 나온 scenario인지 추적 가능하게 만든다.

한 줄 정의:

> Task 6: accepted scenario provenance를 `qa run` report에 연결해 planning → execution lineage를 완성한다.

## Current context / assumptions

현재 완료된 상태:

- Task 1: Newton MVP QA harness
- Task 2: Playwright real execution + failure evidence
- Task 3: deterministic `qa plan`
- Task 4: `qa plan --agent template|codex|claude` agent harness
- Task 5: planning provenance artifact 생성

현재 Task 5 이후 산출물:

- `qa plan`은 accepted scenario YAML을 생성한다.
- `qa plan`은 plan provenance JSON을 생성한다.
- provenance에는 agent, input, prompt, raw output, accepted scenario path, validation status/error가 들어간다.

아직 없는 것:

- `qa run` report가 이 scenario가 어떤 planning run에서 나온 것인지 모른다.
- planning artifact와 execution artifact가 파일 수준에서 분리되어 있다.
- Ouroboros식 lineage의 최소 연결고리인 `plan artifact -> scenario -> run report/evidence`가 아직 닫히지 않았다.

## Why this should be the next goal

이 단계가 좋은 이유:

- 이미 있는 planning layer와 execution layer를 연결한다.
- 새 agent 기능, retry, ranking, semantic judge 없이도 Newton의 정체성이 더 분명해진다.
- 실패 screenshot/trace가 생겼을 때 “이 scenario는 어떤 agent prompt/raw output에서 왔나?”를 추적할 수 있다.
- Ouroboros의 EventStore 전체를 만들지 않고도 local-file lineage MVP를 얻는다.
- crabbox식 실행 evidence와 Ouroboros식 artifact lineage가 처음으로 만난다.

## Non-goals

Task 6에서는 하지 않는다:

- multi-agent comparison
- Codex vs Claude ranking
- semantic judge
- self-healing loop
- auto retry
- 자동으로 `qa plan` 직후 `qa run` 실행
- DB/event store 도입
- cloud/sandbox orchestration
- flaky test management
- dashboard/UI

## Proposed approach

최소 구현은 `qa run`에 optional provenance input을 받는 것이다.

예상 CLI:

```bash
newton qa run qa/scenarios/login-smoke.generated.yaml \
  --base-url http://127.0.0.1:8000 \
  --plan-provenance qa/generated/login_ticket.codex.plan.json
```

실행 report에 다음 정보를 추가한다:

```json
{
  "planning_provenance_path": "qa/generated/login_ticket.codex.plan.json",
  "planning_agent": "codex",
  "planning_input_path": "tests/fixtures/inputs/login_ticket.md",
  "planning_validation_status": "accepted"
}
```

핵심은 `qa run`이 provenance를 재해석하거나 agent를 다시 호출하지 않는 것이다.
단순히 provenance JSON을 읽고, report에 link metadata로 복사한다.

## Step-by-step plan

### 1. Existing report schema 확인

확인할 파일:

- `src/newton/reporting.py`
- `src/newton/runner.py`
- `src/newton/cli.py`
- `tests/test_reporting.py`
- `tests/test_runner.py`
- `tests/test_cli.py`

확인할 것:

- 현재 report JSON 구조
- run metadata가 들어가는 위치
- CLI에서 report path를 어떻게 출력하는지

### 2. RED test 작성

우선 실패 테스트를 작성한다.

권장 테스트:

- `tests/test_runner.py`
  - `qa run` 실행 결과 report에 planning provenance metadata가 포함되는지 검증
- `tests/test_cli.py`
  - `newton qa run ... --plan-provenance <file>` end-to-end 검증
- 필요하면 `tests/test_reporting.py`
  - report serialization이 planning metadata를 유지하는지 검증

테스트 fixture:

- 임시 scenario YAML
- 임시 provenance JSON

최소 provenance fixture 예:

```json
{
  "agent": "codex",
  "input_path": "tests/fixtures/inputs/login_ticket.md",
  "target": "web",
  "base_url": "http://127.0.0.1:8000",
  "prompt_path": "out/login_ticket.codex.prompt.txt",
  "raw_output_path": "out/login_ticket.codex.raw.txt",
  "accepted_scenario_path": "out/login-smoke.generated.yaml",
  "validation_status": "accepted",
  "validation_error": null
}
```

### 3. Minimal provenance reader 추가

가능하면 새 큰 abstraction을 만들지 않는다.

후보:

- 기존 `src/newton/plan_provenance.py`에 read helper 추가

예상 함수:

```python
def load_plan_provenance(path: Path) -> dict[str, Any]:
    ...
```

검증은 최소만 한다:

- JSON parse 가능해야 함
- object/dict여야 함
- 필요한 key가 없으면 hard fail보다 metadata를 가능한 범위만 복사하는 방향 고려

단, `validation_status != "accepted"`인 provenance를 `qa run --plan-provenance`에 넘겼을 때는 에러 처리하는 편이 안전하다.

### 4. Runner/report에 optional metadata 전달

`qa run` 실행 경로에 optional `planning_provenance_path`를 전달한다.

가능한 형태:

- `runner.run_scenario(..., planning_provenance_path: Path | None = None)`
- report payload에 `planning` 또는 `plan_provenance` section 추가

권장 JSON section:

```json
"planning": {
  "provenance_path": "...",
  "agent": "codex",
  "input_path": "...",
  "accepted_scenario_path": "...",
  "validation_status": "accepted"
}
```

이름은 `planning`이 가장 간단하다.

### 5. CLI option 추가

`newton qa run`에 옵션 추가:

```bash
--plan-provenance PATH
```

동작:

- 옵션이 없으면 기존 동작 100% 유지
- 옵션이 있으면 provenance JSON 읽기
- `validation_status != accepted`이면 명확한 에러
- report에 planning metadata 포함

### 6. Docs 업데이트

업데이트할 문서:

- `README.md`
- `docs/agent-runtime-usage.md`
- `docs/qa-planning.md`

문서에 보여줄 최소 workflow:

```bash
newton qa plan ticket.md --agent codex --target web --base-url http://127.0.0.1:8000 --out qa/generated

newton qa run qa/generated/login-smoke.generated.yaml \
  --base-url http://127.0.0.1:8000 \
  --plan-provenance qa/generated/ticket.codex.plan.json
```

설명:

- planning provenance는 scenario 생성 근거다.
- execution report는 실제 실행 evidence다.
- `--plan-provenance`는 둘을 연결하는 optional link다.

### 7. Verification

Focused tests:

```bash
pytest tests/test_runner.py tests/test_cli.py tests/test_reporting.py -q
```

Full tests:

```bash
pytest -q
```

기존 full verification convention을 따르면:

```bash
/opt/homebrew/bin/uv run --python 3.13 --with-editable '.[dev,web]' pytest -q
rm -f uv.lock
```

수동 smoke:

```bash
newton qa plan tests/fixtures/inputs/login_ticket.md \
  --agent template \
  --target web \
  --base-url http://127.0.0.1:8000 \
  --out /tmp/newton-task6

newton qa run /tmp/newton-task6/login-smoke.generated.yaml \
  --base-url http://127.0.0.1:8000 \
  --plan-provenance /tmp/newton-task6/login_ticket.template.plan.json
```

확인할 것:

- run report JSON 생성
- report 안에 `planning.provenance_path` 포함
- report 안에 `planning.agent == "template"`
- 기존 `qa run` without `--plan-provenance`는 깨지지 않음

## Files likely to change

예상 변경 파일:

- `src/newton/cli.py`
  - `qa run --plan-provenance` 옵션 추가
- `src/newton/runner.py`
  - run result/report 생성 경로에 planning metadata 전달
- `src/newton/reporting.py`
  - report JSON에 optional planning section 포함
- `src/newton/plan_provenance.py`
  - provenance JSON read helper 추가 가능
- `tests/test_cli.py`
  - CLI 옵션 end-to-end 테스트
- `tests/test_runner.py`
  - runner metadata propagation 테스트
- `tests/test_reporting.py`
  - report serialization 테스트
- `README.md`
- `docs/qa-planning.md`
- `docs/agent-runtime-usage.md`

## Risks and tradeoffs

### Risk: `qa run`이 planning layer에 과하게 의존할 수 있음

대응:

- `--plan-provenance`는 optional로 유지한다.
- provenance가 없어도 기존 `qa run`은 동일하게 동작한다.
- runner는 agent를 호출하지 않고 JSON metadata만 읽는다.

### Risk: report schema가 커질 수 있음

대응:

- `planning` section을 optional small object로 제한한다.
- raw prompt/raw output 내용을 report에 embed하지 않는다.
- path/reference만 남긴다.

### Risk: rejected provenance를 실행에 연결할 수 있음

대응:

- `validation_status == "accepted"`만 허용한다.
- rejected provenance를 넘기면 CLI에서 명확하게 실패한다.

## Open questions

1. 옵션 이름은 `--plan-provenance`로 충분한가?
   - 추천: yes. 명확하고 작다.

2. `qa plan`이 자동으로 다음 `qa run` 명령을 출력해야 하나?
   - Task 6에서는 하지 않는 것을 추천.
   - 문서 예시만 추가한다.

3. report에 provenance 전체 JSON을 embed할까, path/link만 둘까?
   - 추천: path/link + 핵심 metadata만 복사.
   - raw output/prompt는 원본 artifact로 남겨 둔다.

## Recommended commit message

```text
feat: link plan provenance to qa run reports
```
