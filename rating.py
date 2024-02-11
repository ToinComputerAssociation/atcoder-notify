import math
def calc(oldrating : float, joincount : int, performance : float):
    #joincount:今回も含めた参加回数
    p = 0.0
    x = 1.0
    joincount -= 1
    for i in range(int(joincount)):
        x *= 0.9
        p += x
    if joincount > 0 and oldrating != 0:
        correction = ((math.sqrt(1.0 - x * x) / (1.0 - x)) - 1.0) / (math.sqrt(19.0) - 1.0) * 1200.0
        if oldrating <= 400:
            oldrating = 400 - math.log(1.0 / oldrating * 400.0, math.e) * 400.0
        oldrating += correction
    if performance <= 400 and performance != 0:
        performance = 400 - math.log(1.0 / performance * 400.0, math.e) * 400.0
    newrating = 800.0 * math.log2((pow(2.0, oldrating / 800.0) * p * 0.9 + pow(2.0, performance / 800.0) * 0.9) / (p * 0.9 + 0.9)) - ((math.sqrt(1.0 - (x * 0.9) * (x * 0.9)) / (1.0 - (x * 0.9))) - 1) / (math.sqrt(19.0) - 1) * 1200
    if newrating <= 400:
        newrating = 400.0 / pow(math.e, (400.0 - newrating) / 400.0)
    newrating = int(newrating)
    return newrating