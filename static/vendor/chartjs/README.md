# Chart.js Vendor Fallback

This folder contains a locally-hosted fallback of Chart.js used when the CDN is unavailable.

Populate it using the script:

- Windows PowerShell:
  scripts\download-chartjs.ps1 -Version 4.4.1

The HTML includes a CDN-first tag with a data-fallback to this file to maintain CSP and availability.
