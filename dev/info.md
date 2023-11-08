
CWorkspace(path-to-workspace)
-> CProject(config-name)
-> CAction(action-id, (CProject))
-> (CActionFactory(CProject))
-> (CActionClassExecutor(action-id, CProjectConfig, dicActCfg, CConfigLaunch)): 
    - e.g. Manifest Action Class (catharsys.plugin.std.action_class.manifest.cls_executor)
    - organizes separation of all configs in separate job blocks.
-> CAction.Launch() -> CActionClassExecutor.Execute()
-> catharsys.action.job.Start(CProject, dicExec, dicArgs)
    - used sDTI of dicExec to dynamically load executor for action, e.g. catharsys.plugins.std.blender.execute
    - calls StartJob(CProject, dicExec, dicArgs) on dynamically loaded executor for action
-> executor is specific for actual action
    - decides on LSF or local execution

