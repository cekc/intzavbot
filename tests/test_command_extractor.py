import pytest
from intzavbot.command_extractor import CommandExtractorBuilder, NoMatch

@pytest.fixture
def cmd_extractor():
    return (
        CommandExtractorBuilder()
            .add(1, "1", "one")
            .add(2, "2", "two")
            .add(3, "3", "three")
            .add(0)
            .build()
    )

@pytest.fixture
def cmd_extractor_no_default():
    return (
        CommandExtractorBuilder()
            .add(1, "1", "one")
            .add(2, "2", "two")
            .add(3, "3", "three")
            .build()
    )
    

def test_simple(cmd_extractor):
    assert cmd_extractor.extract("1") == 1
    assert cmd_extractor.extract("2") == 2
    assert cmd_extractor.extract("3") == 3
    assert cmd_extractor.extract("one") == 1
    assert cmd_extractor.extract("tWo") == 2
    assert cmd_extractor.extract("/THREE\\") == 3
    assert cmd_extractor.extract("1, i, o") == 1
    assert cmd_extractor.extract(" One  O") == 1
    assert cmd_extractor.extract("aaa+two/slash") == 2
    assert cmd_extractor.extract("one, two, three!") in [1, 2, 3]
    assert cmd_extractor.extract("aaa+333/slash") == 0
    assert cmd_extractor.extract("") == 0
    assert cmd_extractor.extract("123") == 0
    assert cmd_extractor.extract("oone two13") == 0


def test_raise(cmd_extractor_no_default):
    with pytest.raises(NoMatch):
        cmd_extractor_no_default.extract("")

    with pytest.raises(NoMatch):
        cmd_extractor_no_default.extract("123")

    with pytest.raises(NoMatch):
        cmd_extractor_no_default.extract("oone two13")

    
