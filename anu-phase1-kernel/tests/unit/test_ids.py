from anu_kernel.ids import uuid7


def test_uuid7_version_and_variant():
    value = uuid7()
    assert value.version == 7
    assert value.variant == "specified in RFC 4122"
