# syntax=docker/dockerfile:1
FROM golang:1.24.8-bookworm@sha256:4ed690d6649d63c312b99a6120025ec79ce3b542968a37da53d6236c7c61a848 AS build
WORKDIR /src
ADD --checksum=sha256:45521908307306e925c98d629e1c17d78c8b72b6ee242b1bfb1409f7d8ee5841 https://codeload.github.com/minio/minio/tar.gz/9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a /tmp/minio.tar.gz
RUN tar -xzf /tmp/minio.tar.gz --strip-components=1 -C /src
COPY ldflags.txt /tmp/ldflags.txt
RUN CGO_ENABLED=0 go build -trimpath -ldflags="$(cat /tmp/ldflags.txt)" -o /out/minio .

FROM gcr.io/distroless/static-debian12:nonroot@sha256:afa5c872c891853ca7fcf1f12c3edb23f7eeef36189728842dd51042ff57f7ab
LABEL org.opencontainers.image.source="https://github.com/minio/minio" \
      org.opencontainers.image.revision="9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a" \
      org.opencontainers.image.version="RELEASE.2025-10-15T17-29-55Z"
COPY --from=build /out/minio /usr/bin/minio
# Preserve existing NFS ownership during upgrade; migrate the data owner separately.
USER 0:0
EXPOSE 9000 9001
ENTRYPOINT ["/usr/bin/minio"]
CMD ["server", "/data", "--console-address", ":9001"]
