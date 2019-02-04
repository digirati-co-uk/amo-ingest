# amo_ingest
Proof of concept / illustrative Python code for pushing IIIF Presentation API resources into the DLCS

## Note

Code is derived from: [https://github.com/digirati-co-uk/pokeit](https://github.com/digirati-co-uk/pokeit)

## DLCS Services

The AMO dedicated instance of the DLCS is provisioned using Terraform, with the containerised services managed on Amazon ECS. There is a service list, with docker hub image names, visible at:

[https://services.dlc-services.africamediaonline.com/](https://services.dlc-services.africamediaonline.com/)

A quick summary of the services are below.

### Presley

Presley is a IIIF Presentation API CRUD service, into which IIIF Presentation API manifests can be POSTed, and which provides APIs for adding new services and content to manifests and canvases.

Presley acts as the integration hub for DLC services, so as each service produces outputs, in the form of annotation lists, or services, it posts the URIs for the output back to the IIIF Presentation API manifest as either otherContent or as services.

Kicking off the ingest of a manifest into the DLCS is begun by POSTing that manifest to Presley.

Once ingested, a Presley version of an AMO manifest can be found at:

```bash
https://presley.dlc-services.africamediaonline.com/iiif/customer/manifest?manifest_id=http://543619071faf560cd5c498efdfa53c2d
```

where the manifest_id is the `@id` in the manifest (e.g. the guid/uuid) as in AMO's case, the manifest URI is not the same as the `@id`.

### Destiny

All of the DLCS services communicate via a message bus (known as Iris) which wraps Amazon SNS and Amazon SQS services in a Python (or Java) wrapper, and which emits messages that trigger updates by services, and which reports back on the status of these messages.

There is a service called Destiny which watches for new content in Presley, and which handles the creation of new processing sessions, and the triggering of services via the creation of new messages.

### Giles

Giles provides a simple Elasticsearch based reporting interface on top of Iris/Destiny, and it's Giles that is monitored by the code in this repository to return updates on the canvas by canvas status of the processing of a manifest.

You can see, for example, the past 4 minutes of traffic by doing:

```bash
curl "https://giles.dlc-services.africamediaonline.com/giles/_search" \
     -H 'Content-Type: application/json; charset=utf-8' \
     -d $'{
  "query": {
    "range": {
      "timestamp": {
        "gte": "now-4m"
      }
    }
  },
  "size": 1000,
  "sort": [
    {
      "timestamp": {
        "order": "desc"
      }
    }
  ]
}'
```

The `Pokeit` code described below makes use of Giles and Destiny to track the process of a manifest in real time.

### Starsky, River and Kingfisher

Starsky is the OCR service, which accepts IIIF Image API resources as input, and triggers the creation of OCR data via Google Vision, or via Tesseract. River and Kingfisher provide services and APIs on top of Starsky, and trigger the processing of the content by downstream services.

Example Starsky API calls:

#### Metadata 

The Metadata returns the hOCR which Starsky generates from Google Vision OCR data.

N.B. currently, the hOCR is a simplified representation of the Google Vision data, in future, this could be extended if richer or different segmentation information is required.

```
https://starsky.dlc-services.africamediaonline.com/metadata/?imageURI=http%3A%2F%2Fststithians.africamediaonline.com%2Floris%2F1860%252F1215_870.jpg
```

The `imageURI` is the URL encoded version of the `info.json` link for the image. 


#### Plaintext

The plaintext API returns plaintext for an image.

```https://starsky.dlc-services.africamediaonline.com/plaintext/?imageURI=http%3A%2F%2Fststithians.africamediaonline.com%2Floris%2F1860%252F1215_870.jpg```

The `imageURI` is the URL encoded version of the `info.json` link for the image. 

#### Plaintextlines

This API returns the plaintext, with linefeeds for the image, as JSON, with the bounding boxes.

N.B. this API needs to know the width and height you wish to retrieve them at, as it can translate/scale based on the canvas dimensions at ingest time.

```https://starsky.dlc-services.africamediaonline.com/plaintextlines/?imageURI=http%3A%2F%2Fststithians.africamediaonline.com%2Floris%2F1860%252F1215_870.jpg&width=2395&height=3532```


### Barbarella

Is the service which accepts new OCR content and ingests it into the Mathmos Elasticsearch index.

### Mathmos

This is the IIIF Content Search service, which provides the indexing of content, and which interacts with Starsky via Barbarella to surface search results as hits that a IIIF viewer can display.

## In Use

The basic flow is:

* new manifest (or updated manifest) in Presley
* Destiny creates a new session and begins sending out messages to the DLCS queue.
* Starsky receives the message and OCRs the Image.
* Kingfisher posts content to the manifest and triggers the ingest into search.
* Barbarella fetches the OCR content from Starsky and indexes into Elasticsearch, when done it posts the search service to the manfiest.
* Mathmos provides the APIs used by the search service.
* Barbarella POSTs the service URI back to the manifest in Presley.

### Pokeit

Pokeit can POST a manifest to Presley and then be configured with some JSON that monitors the output from Giles and Destiny to give you real time reporting on the progress of a manifest through the pipeline.

Pokeit is a useful command-line tool for ingesting content, and also a good set of proof of concept code to look at as a model for writing your own.

N.B. the text pipeline is not really designed for real time viewing of outputs, so `pokeit` is designed to be used one manifest at a time. 
If you want to ingest many manifests, they can be enqueued just by POSTing to Presley using JWT (as can be seen in the pokeit code), without using the real-time monitoring of Giles/Destiny that `pokeit` provides.


#### Usage

To setup a Python environment for pokeit:

* checkout this repo
* setup a Python3 virtualenv (or use pyenv)
* `pip install -r requirements.txt` to install the requirements

```bash
cd /src/
python -s ./resources/amo_success.json http://ststithians.africamediaonline.com/manifest?media_id=1216_1036&depot_id=1860
```

Pokeit will post a manifest to Presley, and stream back the canvas by canvas processing output.

You can see the services being added, and their success or failure. 

N.B. if there are already many existing canvases in the processing queue, pokeit may time out, as it waits for the success messages for just the canvases in this manifest. If there are already many canvases in the queue, it will time out after around 100 seconds.

N.B. __One important thing to note, because the AMO manifests use parameters, and removing the final parameter returns a _different_ manifest for the same content, the manifest URI should be wrapped in quotes.__


### Checkit

Checkit will run through all of the services of a manifest and will check that the services and otherContent on a manifest are valid.


#### Usage

Setup the Python environment as above.

```bash
python checkit.py "https://presley.dlc-services.africamediaonline.com/iiif/customer/manifest?manifest_id=http://543619071faf560cd5c498efdfa53c2d"
```

N.B. note that address for the manifest is a a request to Presley with the original dereferenceable manifest URI as a parameter.

Checkit will work through each service on the manifest and check that the services are operational, and that the otherContent (OCR annotations) are available.

`settings.py` can be configured to just check the annotation lists are present, without dereferencing, which is quicker.

## Presley Checker

I created a simple (very simple!) but of code to work through the uris for the St. Stithians manfiests and check if they are in Presley.

```bash
python presley_checker.py
```

## Settings.py

This contains some keys, so the keys will be sent in another way, to protect the security of your endpoint.


