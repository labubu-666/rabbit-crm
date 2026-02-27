# rabbithole

# Quick start

    uv add git+ssh://git@github.com/labubu-666/rabbithole.git@main 

# Dev

    docker compose up

# Build natively

    uv run rabbithole build

# Build container

    docker build . --tag rabbithole:latest && docker run --publish 80:80 rabbithole:latest  