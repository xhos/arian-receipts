FROM golang:1.25.4-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go build -o /bin/server ./cmd/server

FROM alpine:3.23.2
COPY --from=build /bin/server /bin/server
ENTRYPOINT ["/bin/server"]
