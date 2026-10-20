(* Dedicated batch entry point. Reusable plot files must not call Exit/Quit.
   Usage: wolframscript -file run_plot.wls /absolute/path/plot.wl *)
Module[{args = Rest[$ScriptCommandLine], target, result, exitCode},
  If[Length[args] =!= 1,
    Print["Usage: wolframscript -file run_plot.wls /absolute/path/plot.wl"];
    Quiet[CloseKernels[]]; Exit[64]];
  target = ExpandFileName[First[args]];
  If[! FileExistsQ[target],
    Print["Plot script not found: ", target];
    Quiet[CloseKernels[]]; Exit[66]];
  result = CheckAbort[Check[Get[target], $Failed], $Aborted];
  exitCode = If[result === $Failed || result === $Aborted || FailureQ[result], 1, 0];
  If[exitCode != 0, Print["Plot run failed: ", result]];
  Quiet[CloseKernels[]];
  Exit[exitCode]
]
