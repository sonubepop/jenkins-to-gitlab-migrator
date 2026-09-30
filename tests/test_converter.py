from pathlib import Path

import pytest
import yaml

from jenkins2gitlab import convert
from jenkins2gitlab.converter import map_env_refs

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def conv(body: str, extra: str = "") -> dict:
    src = f"pipeline {{\n agent any\n{extra}\nstages {{ {body} }} }}"
    return yaml.safe_load(convert(src).to_yaml())


def test_simple_stage_becomes_job():
    cfg = conv("stage('Unit Tests') { steps { sh 'pytest -q' } }")
    assert cfg["stages"] == ["unit-tests"]
    assert cfg["unit-tests"]["script"] == ["pytest -q"]


def test_docker_agent_becomes_default_image():
    src = "pipeline { agent { docker { image 'python:3.12' } } stages { stage('a') { steps { sh 'x' } } } }"
    cfg = yaml.safe_load(convert(src).to_yaml())
    assert cfg["default"]["image"] == "python:3.12"


def test_parallel_stages_share_a_gitlab_stage():
    cfg = conv("""stage('Checks') { parallel {
        stage('Lint') { steps { sh 'ruff check .' } }
        stage('Test') { steps { sh 'pytest' } } } }""")
    assert cfg["stages"] == ["checks"]
    assert cfg["lint"]["stage"] == cfg["test"]["stage"] == "checks"


def test_when_branch_and_tag_become_rules():
    cfg = conv("""stage('Deploy') { when { branch 'main' } steps { sh './deploy' } }
                  stage('Release') { when { tag 'v*' } steps { sh './release' } }""")
    assert cfg["deploy"]["rules"] == [{"if": '$CI_COMMIT_BRANCH == "main"'}]
    assert cfg["release"]["rules"] == [{"if": "$CI_COMMIT_TAG =~ /^v.*$/"}]


def test_input_makes_job_manual():
    cfg = conv("stage('Prod') { input { message 'Go?' } steps { sh './deploy prod' } }")
    assert cfg["prod"]["when"] == "manual"


def test_retry_is_capped_at_gitlab_maximum():
    cfg = conv("stage('Flaky') { steps { retry(5) { sh './flaky' } } }")
    assert cfg["flaky"]["retry"] == 2


def test_junit_and_archive_become_artifacts():
    cfg = conv("""stage('Test') { steps {
        sh 'pytest --junitxml=r.xml'
        junit 'r.xml'
        archiveArtifacts artifacts: 'dist/*.whl' } }""")
    art = cfg["test"]["artifacts"]
    assert art["reports"]["junit"] == "r.xml"
    assert art["paths"] == ["dist/*.whl"]


def test_credentials_are_never_copied_into_yaml():
    result = convert("""pipeline { agent any
        environment { TOKEN = credentials('secret-id') }
        stages { stage('a') { steps { sh 'echo hi' } } } }""")
    text = result.to_yaml()
    assert "secret-id" not in text.split("Manual review:")[-1].split("\n\n", 1)[-1]
    assert "TOKEN" not in yaml.safe_load(text).get("variables", {})
    assert any("TOKEN" in f.message for f in result.manual_items)


def test_stage_post_failure_uses_job_status():
    cfg = conv("stage('a') { steps { sh 'x' } post { failure { sh 'dump-logs' } } }")
    assert 'CI_JOB_STATUS" = "failed"' in cfg["a"]["after_script"][0]


def test_pipeline_post_becomes_post_stage_jobs():
    src = """pipeline { agent any\n stages { stage('a') { steps { sh 'x' } } }
             post { failure { sh './notify.sh' } } }"""
    cfg = yaml.safe_load(convert(src).to_yaml())
    assert cfg["post-failure"] == {"stage": ".post", "script": ["./notify.sh"], "when": "on_failure"}


def test_checkout_only_stage_is_dropped():
    cfg = conv("stage('Checkout') { steps { checkout scm } } stage('b') { steps { sh 'x' } }")
    assert "checkout" not in cfg and cfg["stages"] == ["b"]


def test_unknown_step_is_reported_not_silently_dropped():
    result = convert("pipeline { agent any\n stages { stage('a') { steps { sh 'x'\n fancyPlugin 'y' } } } }")
    assert any("fancyPlugin" in f.message for f in result.manual_items)


@pytest.mark.parametrize("src,expected", [
    ("echo $BUILD_NUMBER", "echo $CI_PIPELINE_IID"),
    ("echo ${env.BRANCH_NAME}", "echo ${CI_COMMIT_REF_NAME}"),
    ("echo ${params.TARGET}", "echo ${TARGET}"),
    ("echo $GIT_COMMIT_SHORT", "echo $GIT_COMMIT_SHORT"),
])
def test_env_references_are_mapped(src, expected):
    assert map_env_refs(src) == expected


@pytest.mark.parametrize("path", sorted(EXAMPLES.glob("*.Jenkinsfile")), ids=lambda p: p.name)
def test_examples_match_committed_output(path):
    expected = path.with_name(path.name.replace(".Jenkinsfile", ".gitlab-ci.yml")).read_text()
    assert convert(path.read_text()).to_yaml() == expected


def test_install_only_stage_moves_to_before_script():
    cfg = conv("""stage('Install') { steps { sh 'pip install -r requirements.txt' } }
                  stage('Test') { steps { sh 'pytest' } }""")
    assert "install" not in cfg and cfg["stages"] == ["test"]
    assert cfg["default"]["before_script"] == ["pip install -r requirements.txt"]


def test_escaped_dollar_in_double_quotes_becomes_shell_variable():
    cfg = conv('stage(\'a\') { steps { sh "echo \\$HOME" } }')
    assert cfg["a"]["script"] == ["echo $HOME"]
