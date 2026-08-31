from evaluation.cases import all_cases


def test_exact_cases(): assert len(all_cases())==10
def test_labels(): assert sum(c['expected']=='RISK' for c in all_cases())==7
