from dataclasses import dataclass


@dataclass(frozen=True)
class Metrics:
 total:int; correct:int; tp:int; tn:int; fp:int; fn:int
 @property
 def accuracy(self): return self.correct/self.total if self.total else 0.0
def calculate(expected,actual):
 tp=sum(e and a for e,a in zip(expected,actual)); tn=sum((not e) and (not a) for e,a in zip(expected,actual)); fp=sum((not e) and a for e,a in zip(expected,actual)); fn=sum(e and (not a) for e,a in zip(expected,actual)); return Metrics(len(expected),tp+tn,tp,tn,fp,fn)
