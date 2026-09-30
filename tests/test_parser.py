import pytest

from jenkins2gitlab.parser import ParseError, parse, strip_comments


def test_parses_nested_blocks_and_statements():
    pipe = parse("""
    pipeline {
        agent any
        stages {
            stage('Build') {
                steps { sh 'make' }
            }
        }
    }""")
    stage = pipe.block("stages").blocks("stage")[0]
    assert stage.args == "'Build'"
    assert stage.block("steps").statements()[0].text == "sh 'make'"


def test_braces_inside_strings_are_ignored():
    pipe = parse("""pipeline { stages { stage('x') { steps { sh 'echo "{not a block}"' } } } }""")
    step = pipe.block("stages").blocks("stage")[0].block("steps").statements()[0]
    assert step.text == """sh 'echo "{not a block}"'"""


def test_triple_quoted_multiline_string_is_one_statement():
    pipe = parse('''pipeline { stages { stage('x') { steps {
        sh """
            echo one
            echo two
        """
    } } } }''')
    steps = pipe.block("stages").blocks("stage")[0].block("steps").statements()
    assert len(steps) == 1 and "echo two" in steps[0].text


def test_comments_are_removed_but_not_inside_strings():
    src = "a // comment\nsh 'http://example.com' /* block */"
    cleaned = strip_comments(src)
    assert "comment" not in cleaned and "block" not in cleaned
    assert "http://example.com" in cleaned


def test_statement_continues_after_trailing_comma():
    pipe = parse("""pipeline { stages { stage('x') { steps {
        archiveArtifacts artifacts: 'dist/*',
                         fingerprint: true
    } } } }""")
    steps = pipe.block("stages").blocks("stage")[0].block("steps").statements()
    assert len(steps) == 1 and "fingerprint" in steps[0].text


def test_missing_pipeline_block_raises():
    with pytest.raises(ParseError):
        parse("node { sh 'make' }")


def test_unbalanced_braces_raise():
    with pytest.raises(ParseError):
        parse("pipeline { stages { ")
