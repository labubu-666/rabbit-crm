# rabbithole

# Dev

    docker compose up

# Build natively

    uv run rabbithole build

# Build container

    docker build . --tag rabbithole:latest && docker run --publish 80:80 rabbithole:latest  