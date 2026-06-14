from tracktrace.traceapi.validators import (
    build_awb_number,
    build_container_number,
    is_valid_awb,
    is_valid_container_number,
)


def test_container_check_digit_roundtrip():
    num = build_container_number("MSKU", "076259")
    assert is_valid_container_number(num)


def test_container_rejects_bad_check_digit():
    good = build_container_number("MSKU", "076259")
    wrong = good[:-1] + str((int(good[-1]) + 1) % 10)
    assert not is_valid_container_number(wrong)


def test_container_rejects_bad_format():
    assert not is_valid_container_number("MSK0762594")   # only 3 letters incl no category
    assert not is_valid_container_number("MSKX0762594")  # category must be U/J/Z


def test_awb_check_digit_roundtrip():
    awb = build_awb_number("160", "4421890")
    assert is_valid_awb(awb)
    assert is_valid_awb("160-4421890" + awb[-1])  # accepts dash formatting


def test_awb_rejects_bad_check_digit():
    awb = build_awb_number("160", "4421890")
    wrong = awb[:-1] + str((int(awb[-1]) + 1) % 10)
    assert not is_valid_awb(wrong)
