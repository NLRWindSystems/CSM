from csm.model._base import CSM
import pandas as pd


class Basic(CSM):
    def c(a, b):
        return a + b + 1

    def d(c, a):
        return a + c + 1

    def e(d):
        return d + 1


class DataFrame(CSM):

    def df_output(a, b) -> pd.DataFrame:
        num_rows = 3
        result = pd.DataFrame(data={"a": [a] * num_rows, "b": [b] * num_rows})
        result = result.rename_axis("test_index_name")
        return result


class DataFrameNoArgs(CSM):
    def df_output() -> pd.DataFrame:
        return pd.DataFrame({"a": [1, 2], "b": [4, 5]}).rename_axis("test_index_name")


class Recursive(CSM):
    def x(y):
        return y * 2

    def y(x):
        return x / 2


class MissingReturnTypeHint(CSM):

    def df_output(a, b):
        num_rows = 3
        result = pd.DataFrame(data={"a": [a] * num_rows, "b": [b] * num_rows})
        return result


class NoFunctions(CSM):
    pass
