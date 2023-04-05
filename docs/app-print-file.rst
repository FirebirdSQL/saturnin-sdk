
PRINT FILE application
======================

Metadata
--------

name:
  saturnin.app.print_file

description:
  Print text file application

classification:
  text/print

OID:
  None

OID name:
  None

UUID:
  826ecaca-d3b6-11ed-97b5-5c879cc92822

facilities:
  None

API:
  None

Description
-----------

This example Saturnin application prints a text file on screen with optional syntax highlight.

It runs the preconfigured bundle container with `saturnin.text.reader` and `saturnin.text.writer`
microservices to print file to `stdout`. The captured `stdout` is then printed to console
with applied syntaxt highlight.

It demostrates:

- how Saturnin recipe used by application could be generated when `install recipe` command
  is executed with `--app-id` parameter.
- how the application (a `typer` command) access the recipe that is associated with its
  invokation.


