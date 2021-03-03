================================
Saturnin test dummy microservice
================================

This microservice does nothing, and is intended for testing of service management machinery.

It's possible to configure the service to fail (raise an exception) during `initialize()`,
`aquire_resources()`, `release_resources()`, `start_activities()` or `stop_activities()`.
