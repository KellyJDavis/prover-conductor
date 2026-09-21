import Mathlib

/-- A "warm" Lean process: Mathlib loaded, state kept in a counter, one line appended per tick. -/
def main : IO Unit := do
  IO.println "ready"
  (← IO.getStdout).flush
  let mut n := 0
  repeat
    n := n + 1
    IO.FS.withFile "/mnt/hb" .append fun h => h.putStrLn s!"{n}"
    IO.sleep 200
