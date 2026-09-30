from jenkins2gitlab.cli import main

SRC = "pipeline { agent any\n stages { stage('a') { steps { sh 'make'\n mystery 'x' } } } }"


def test_cli_writes_output_and_report(tmp_path):
    jf = tmp_path / "Jenkinsfile"
    jf.write_text(SRC)
    out, rep = tmp_path / ".gitlab-ci.yml", tmp_path / "report.md"
    assert main([str(jf), "-o", str(out), "--report", str(rep)]) == 0
    assert "make" in out.read_text()
    assert "- [ ]" in rep.read_text()


def test_strict_mode_fails_when_manual_work_remains(tmp_path):
    jf = tmp_path / "Jenkinsfile"
    jf.write_text(SRC)
    assert main([str(jf), "-o", str(tmp_path / "o.yml"), "--strict"]) == 2


def test_invalid_input_returns_error(tmp_path, capsys):
    jf = tmp_path / "Jenkinsfile"
    jf.write_text("node { }")
    assert main([str(jf)]) == 1
    assert "declarative" in capsys.readouterr().err
