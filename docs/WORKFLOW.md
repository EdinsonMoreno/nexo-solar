# Desarrollo de Nexo Solar

Repositorio privado: https://github.com/EdinsonMoreno/nexo-solar

Autor: Edinson Andres Moreno Cepeda.

## Ramas

- `dev`: desarrollo de funciones y correcciones. Es la rama de trabajo local inicial.
- `QA`: validación de los cambios provenientes de `dev`.
- `main`: versiones aprobadas y listas para despliegue. Rama predeterminada del repositorio.

## Promoción

1. Desarrollar y registrar cambios en `dev`.
2. Abrir un pull request de `dev` hacia `QA` y ejecutar las pruebas aplicables.
3. Corregir problemas en `dev` y volver a promover a `QA`.
4. Tras validar, abrir un pull request de `QA` hacia `main`.
5. Desplegar la versión aprobada de `main` cuando se defina el destino de entrega.

Los merges de promoción deben conservar la relación entre ramas; no usar squash ni rebase entre estas ramas permanentes. No hay despliegue automático ni protecciones de rama configuradas. El workflow heredado de comprobaciones se ejecuta en las tres ramas y no construye instaladores.

## Base inicial

El repositorio comienza con historial nuevo y sin remotos del proyecto anterior. Las tres ramas nacen del mismo commit. La interfaz y varios identificadores internos conservan la base anterior hasta la fase de rediseño; no se han implementado funciones Davis todavía.

Las especificaciones Davis se encuentran en `.kiro/specs/davis-weatherlink-reader/`.

La configuración local, bases SQLite, datos medidos, logs y entornos virtuales permanecen fuera de Git. Para preparar una instalación, copiar `modbuspython/config.example.yaml` a `config.yaml` y completar los parámetros locales. Las bases se crean mediante la aplicación; no se distribuyen datos de la estación en el repositorio.

No ejecutar builds sin solicitud explícita del propietario.
