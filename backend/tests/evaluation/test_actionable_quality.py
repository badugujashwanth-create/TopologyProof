from evaluation.actionable_quality import CriterionResult, QualityScore, evaluate


def test_six_criteria_and_derived_total():
 result=evaluate(); assert len(result['baseline']['criteria'])==6; assert result['baseline']['total']==sum(c['satisfied'] for c in result['baseline']['criteria'])
def test_all_false_and_true_totals():
 assert QualityScore('x',tuple(CriterionResult(f'C{i}',False,'','') for i in range(6))).total==0
 assert QualityScore('x',tuple(CriterionResult(f'C{i}',True,'e','s') for i in range(6))).total==6
def test_real_artifacts_load():
 result=evaluate(); assert result['topologyproof']['criteria'][1]['evidence']
