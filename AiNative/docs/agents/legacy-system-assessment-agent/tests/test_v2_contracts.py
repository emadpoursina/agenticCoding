"""Static contract tests for the Legacy System Assessment V2 DAG and artifacts.

Validates dag.json topology (order, acyclicity, producer coverage, worker
coverage, parallel-group independence) and that the prose contracts
(workflow.md / methodology.md / rule.md / orchestrator.md / workers.md / schemas.md)
contain the V2 markers the DAG and Definition of Done depend on.

Stdlib only: python3 -m unittest discover -s tests
"""
import json
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def load_dag():
    with open(BASE / "dag.json") as f:
        return json.load(f)


def read(name):
    return (BASE / name).read_text()


EXPECTED_ORDER = [
    "boundary", "recon", "evidence", "reconcile", "system",
    "scenarios", "gate", "strategies", "breakdown", "estimates", "synthesis",
]

REPORT_SECTIONS = [
    "Executive Summary", "Assessment Scope", "System Profile",
    "Current Architecture", "Implementation Condition", "Changeability",
    "Risks", "Behavior", "Findings", "Modernization Options",
    "Work Breakdown", "Engineering Effort", "Calendar-Time",
    "AI Execution", "AI Token", "Assumptions", "Unknowns",
    "Further Investigation", "Evidence Index",
]


class TestDagTopology(unittest.TestCase):
    def test_version(self):
        self.assertEqual(load_dag()["version"], "2")

    def test_stage_order(self):
        ids = [s["id"] for s in load_dag()["stages"]]
        self.assertEqual(ids, EXPECTED_ORDER)

    def test_stages_have_refs(self):
        for s in load_dag()["stages"]:
            for key in ("id", "consumes", "produces", "ref"):
                self.assertIn(key, s, f"stage {s.get('id')} missing {key}")

    def test_acyclic_producer_coverage(self):
        """Every consumed artifact must be produced by a strictly earlier stage."""
        produced = {}
        for i, s in enumerate(load_dag()["stages"]):
            for art in s["consumes"]:
                self.assertIn(
                    art, produced,
                    f"stage {s['id']} consumes {art}, never produced upstream",
                )
                self.assertLess(
                    produced[art], i,
                    f"stage {s['id']} consumes {art} from a later stage",
                )
            for art in s["produces"]:
                self.assertNotIn(
                    art, produced, f"artifact {art} produced twice"
                )
                produced[art] = i

    def test_required_workers_dispatched(self):
        dag = load_dag()
        dispatched = set()
        for s in dag["stages"]:
            dispatched.update(s.get("workers", []))
            dispatched.update(s.get("optional_workers", []))
        for w in dag["required_workers"]:
            self.assertIn(w, dispatched, f"required worker {w} never dispatched")

    def test_spec_worker_list_covered(self):
        """V2 spec section 2 names 13 analysis workers; all must be required."""
        spec_workers = [
            "repo-scout", "static-analyst", "architecture-analyst",
            "history-analyst", "system-understanding-analyst",
            "behavior-test-analyst", "contradiction-reconciler",
            "changeability-analyst", "risk-analyst",
            "change-scenario-selector", "refactor-strategy-planner",
            "incremental-replacement-planner", "rewrite-strategy-planner",
        ]
        required = load_dag()["required_workers"]
        for w in spec_workers:
            self.assertIn(w, required, f"spec worker {w} missing from DAG")

    def test_parallel_groups_independent(self):
        """Workers in a parallel group must share one parallel stage."""
        dag = load_dag()
        stage_of = {}
        for s in dag["stages"]:
            for w in s.get("workers", []):
                stage_of[w] = (s["id"], s.get("parallel", False))
        for group in dag["parallel_groups"]:
            stages = {stage_of[w][0] for w in group}
            self.assertEqual(len(stages), 1,
                             f"parallel group {group} spans stages {stages}")
            stage = next(iter(stages))
            self.assertTrue(stage_of[group[0]][1],
                            f"stage {stage} not marked parallel")

    def test_synthesis_constrained(self):
        synth = [s for s in load_dag()["stages"] if s["id"] == "synthesis"][0]
        self.assertIn("evidence-synthesizer", synth["workers"])
        self.assertTrue(synth.get("forbids"),
                        "synthesis must forbid inventing findings")

    def test_gate_has_stopping_question(self):
        gate = [s for s in load_dag()["stages"] if s["id"] == "gate"][0]
        self.assertIn("stopping_question", gate)
        self.assertEqual(gate["owner"], "orchestrator")


class TestProseContracts(unittest.TestCase):
    def test_agent_stages_and_workers(self):
        agent = read("workflow.md")
        for n in range(11):
            self.assertIn(f"Stage {n}", agent)
        for w in ("repo-scout", "contradiction-reconciler",
                  "change-scenario-selector", "work-breakdown-planner",
                  "estimator", "evidence-synthesizer"):
            self.assertIn(w, agent, f"workflow.md never delegates to {w}")

    def test_agent_report_structure(self):
        agent = read("workflow.md")
        for section in REPORT_SECTIONS:
            self.assertIn(section, agent, f"report section missing: {section}")

    def test_skill_models(self):
        skill = read("methodology.md")
        for marker in ("id: EVID-", "id: FIND-", "id: CONTR-",
                       "resolution_status:", "resolution:",
                       "agent_friendly", "low\n", "expected\n", "high"):
            self.assertIn(marker, skill, f"methodology.md missing marker: {marker!r}")

    def test_rule_constraints(self):
        rules = read("rule.md")
        for marker in ("Evidence before conclusions",
                       "universal",  # no universal quality score
                       "rewrite before assessing",
                       "ranges",  # estimates must be ranges
                       "Separate engineering effort from calendar time",
                       "Never invent model pricing",
                       "never be represented as absence of a problem"):
            self.assertIn(marker, rules, f"rule.md missing: {marker!r}")

    def test_workers_cover_dag(self):
        workers = read("workers.md")
        for w in load_dag()["required_workers"]:
            self.assertIn(w, workers, f"workers.md missing contract: {w}")

    def test_schemas_cover_artifacts(self):
        schemas = read("schemas.md")
        for marker in ("EVID-", "FIND-", "CONTR-", "WP-",
                       "assessment-boundary", "repo-profile",
                       "change-scenarios", "risk-register",
                       "Strategy assessment", "Work package",
                       "calendar_time", "pricing_source",
                       "Failure record"):
            self.assertIn(marker, schemas, f"schemas.md missing: {marker!r}")

    def test_orchestrator_mechanics(self):
        orch = read("orchestrator.md")
        for marker in ("dag.json", "Artifact registry", "Retries",
                       "stopping", "Token / cost accounting",
                       "Failure and missing-evidence",
                       "Completion check"):
            self.assertIn(marker, orch, f"orchestrator.md missing: {marker!r}")


if __name__ == "__main__":
    unittest.main()
