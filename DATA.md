# NLI Data Documentation

## manifests

### sources
* start from http://iiif.nli.org.il/collections/root.json
* download each collection's json (e.g. http://iiif.nli.org.il/collections/tma.json).
* then download each item's manifest metadata (e.g. http://iiif.nli.org.il/IIIFv21/DOCID/NNL01_TMA003426736/manifest)
* The aggregation of this data is the `manifests` dataset
* Primary key is the system number
* Each manifest has 1 or more related `sequences`

### High-Level Overview

