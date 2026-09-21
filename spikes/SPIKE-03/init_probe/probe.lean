import Lean
open Lean
unsafe def main (args : List String) : IO UInt32 := do
  initSearchPath (← findSysroot)
  let enable := args[0]! == "enable"
  let loadExts := args[1]! == "exts"
  if enable then enableInitializersExecution
  try
    let _env ← importModules #[{ module := `Evil }] {} (loadExts := loadExts)
    IO.println s!"imported enable={enable} loadExts={loadExts}"
  catch e => IO.println s!"import threw enable={enable} loadExts={loadExts}: {e}"
  return 0
