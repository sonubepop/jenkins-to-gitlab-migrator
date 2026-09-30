FROM python:3.12-slim AS build
WORKDIR /src
COPY pyproject.toml README.md ./
COPY jenkins2gitlab ./jenkins2gitlab
RUN pip wheel --no-deps -w /wheels .

FROM python:3.12-slim
RUN useradd --create-home --uid 10001 app
COPY --from=build /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels
USER app
WORKDIR /work
ENTRYPOINT ["jenkins2gitlab"]
CMD ["--help"]
