(* Run with TestReport after Get["C6Project.wl"]. Not executed by producer. *)
VerificationTest[AssociationQ[C6Project`C6Capabilities[]], True,
 TestID -> "capability-report-is-association"]
VerificationTest[C6Project`C6Capabilities[]["Normalization"], "r6 = 2187 C6(1)",
 TestID -> "normalization"]
VerificationTest[AssociationQ[C6Project`C6RecommendedSpecification[]], True,
 TestID -> "canonical-real-specification-loads"]
VerificationTest[C6Project`C6Capabilities[]["FiniteBuiltInOnlyFullClosedFormEstablished"], False,
 TestID -> "no-false-built-in-closed-form-claim"]
