---
title: "Celery."
---

# Task-Verlust bei Absturz

Standardmäßig vergisst Celery einen Task sobald ein Worker ihn aufnimmt. Stürtzt der Worker ab oder wird er neu gestartet, ist der Task weg.