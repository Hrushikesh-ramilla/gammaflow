# Build stage
FROM golang:1.22-alpine AS builder

RUN apk add --no-cache git

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /raftkv ./cmd/server

# Runtime stage
FROM alpine:3.19

RUN apk add --no-cache ca-certificates && \
    adduser -D -u 1000 raftkv

COPY --from=builder /raftkv /usr/local/bin/raftkv

USER raftkv
WORKDIR /home/raftkv

EXPOSE 8080 9090

ENTRYPOINT ["raftkv"]
