from evaluation.metrics import calculate


def test_metrics():
 m=calculate([1,1,0,0],[1,0,1,0]); assert (m.tp,m.tn,m.fp,m.fn)==(1,1,1,1)
