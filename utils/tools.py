from datetime import timedelta


def todelta(time):
    value = float(time[:-1])
    dtype = time[-1]
    if dtype == "d":
        return timedelta(days=value)
    if dtype == "h":
        return timedelta(hours=value)
    if dtype == "m":
        return timedelta(minutes=value)
    if dtype == "s":
        return timedelta(seconds=value)
