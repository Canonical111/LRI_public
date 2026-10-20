from pathlib import Path
from decimal import Decimal,localcontext
import json
R=Path(__file__).resolve().parents[1]
a=json.loads((R/'verification/run80.json').read_text());b=json.loads((R/'verification/run110dfs.json').read_text())
with localcontext() as ctx:
 ctx.prec=125
 differences={k:str(abs(Decimal(a['values'][k])-Decimal(v))) for k,v in b['values'].items()}
 assert all(Decimal(x)<Decimal('1e-63') for x in differences.values())
 u=Decimal(b['values']['U'])
 report={'status':'completed_numerical_evaluation_of_archived_exact_F2_expression','U':str(u),'three_quarters_U':str(3*u/4),'runs':['run80.json','run110dfs.json'],'differences':differences,'new_decimal_vs_gmp_subset_check_pending':True,'interval_certified':False,'higher_logarithm_check':'not replayable from surviving scalar-only F2 files; NOT marked passed','no_new_high_order_integration_claimed':True}
 (R/'verification/numerical_comparison.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
