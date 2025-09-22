from app.utils import to_mapping


class RowLike:
    def __init__(self, data):
        self._data = data

    def keys(self):
        return list(self._data.keys())

    def __getitem__(self, k):
        return self._data[k]


def test_to_mapping_with_dict():
    d = {"a": 1, "b": 2}
    assert to_mapping(d) == d


def test_to_mapping_with_row_like():
    r = RowLike({"x": 10, "y": 20})
    assert to_mapping(r) == {"x": 10, "y": 20}


def test_to_mapping_with_none_and_non_mapping():
    assert to_mapping(None) == {}
    # object without keys

    class Foo:
        pass

    assert to_mapping(Foo()) == {}


def test_to_mapping_with_mapping_view_like():
    d = {"k": 1}
    mv = d.keys()  # mapping view
    # emulate an object that returns this view from keys()
    class KObj:

        def keys(self):
            return mv

        def __getitem__(self, k):
            return d[k]

    assert to_mapping(KObj()) == d
