def test_package_imports():
    import hermes_kanban

    assert hermes_kanban.__version__ == "1.7.0"
    assert hermes_kanban.AgentExecutor
    assert hermes_kanban.ExecutionSettings
    assert hermes_kanban.ExecuteResult
    assert hermes_kanban.StepStartRequest
    assert hermes_kanban.HarnessResult
    assert hermes_kanban.PiHarnessAdapter
