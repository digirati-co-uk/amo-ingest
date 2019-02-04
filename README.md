# amo_ingest
Proof of concept / illustrative Python code for pushing IIIF Presentation API resources into the DLCS

## Note

Code is derived from: [https://github.com/digirati-co-uk/pokeit](https://github.com/digirati-co-uk/pokeit)

## DLCS Services

The AMO dedicated instance of the DLCS is provisioned using Terraform, with the containerised services managed on Amazon ECS. There is a service list, with docker hub image names, visible at:

https://services.dlc-services.africamediaonline.com/

A quick summary of the services are below.

### Presley

Presley is a IIIF Presentation API CRUD service, into which IIIF Presentation API manifests can be POSTed, and which provides APIs for adding new services and content to manifests and canvases.

Presley acts as the integration hub for DLC services, so as each service produces outputs, in the form of annotation lists, or services, it posts the URIs for the output back to the IIIF Presentation API manifest as either otherContent or as services.

Kicking off the ingest of a manifest into the DLCS is begun by POSTing that manifest to Presley.

### Destiny

All of the DLCS services communicate via a message bus (known as Iris) which wraps Amazon SNS and Amazon SQS services in a Python (or Java) wrapper, and which emits messages that trigger updates by services, and which reports back on the status of these messages.

There is a service called Destiny which watches for new content in Presley, and which handles the creation of new processing sessions, and the triggering of services via the creation of new messages.

### Giles

Giles provides a simple Elasticsearch based reporting interface on top of Iris/Destiny, and it's Giles that is monitored by the code in this repository to return updates on the canvas by canvas status of the processing of a manifest.

### Starsky

Starsky is the OCR service, which accepts IIIF Image API resources as input, and triggers the creation of OCR data via Google Vision, or via Tesseract.

### River and Kingfisher

River and Kingfisher provide services and APIs on top of Starsky, and trigger the processing of the content by downstream services.

### Barbarella

Is the service which accepts new OCR content and ingests it into the Mathmos Elasticsearch index.

### Mathmos

This is the IIIF Conten Search service, which provides the indexing of content, and which interacts with Starsky via Barbarella to surface search results as hits that a IIIF viewer can display.

## In Use

The basic flow is:

* new manifest (or updated manifest) in Presley
* Destiny creates a new session and begins sending out messages to the DLCS queue.
* Starsky receives the message and OCRs the Image.
* Kingfisher posts content to the manifest and triggers the ingest into search.
* Barbarella fetches the OCR content from Starsky and indexes into Elasticsearch, when done it posts the search service to the manfiest.
* Mathmos provides the APIs used by the search service.

### Pokeit

Pokeit can POST a manifest to Presley and then be configured with some JSON that monitors the output from Giles and Destiny to give you real time reporting on the progress of a manifest through the pipeline.

Pokeit is a useful command-line tool for ingesting content, and also a good set of proof of concept code to look at as a model for writing your own.

### Checkit

Checkit will run through all of the services of a manifest and will check that the services and otherContent on a manifest are valid.

### Hokeypokey

Hokeypokey uses Pokeit to ingest a manifest and then uses Checkit to validate the output.


