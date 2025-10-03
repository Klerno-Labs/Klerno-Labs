from typing import Any

from app.utils import to_mapping


class RowLike:
    def __init__(self, data) -> None:
        self._data = data

    def keys(self) -> None:
        return list[Any](self._data.keys())

    def __getitem__(self, k) -> None:
        return self._data[k]


def test_to_mapping_with_dict() -> None:
    d = {"a": 1, "b": 2}
    assert to_mapping(d) == d


def test_to_mapping_with_row_like() -> None:
    r = RowLike({"x": 10, "y": 20})
    assert to_mapping(r) == {"x": 10, "y": 20}


def test_to_mapping_with_none_and_non_mapping() -> None:
    assert to_mapping(None) == {}
    # object without keys

    # nested simple class to emulate non-mapping object
    class Foo:
        pass

    assert to_mapping(Foo()) == {}


def test_to_mapping_with_mapping_view_like() -> None:
    d = {"k": 1}
    mv = d.keys()  # mapping view
    # emulate an object that returns this view from keys()

    class KObj:
        def keys(self) -> None:
            return mv

        def __getitem__(self, k) -> None:
            return d[k]

    assert to_mapping(KObj()) == d
