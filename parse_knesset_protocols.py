from datapackage_pipelines.wrapper import ingest, spew
from dotenv import load_dotenv, find_dotenv
import logging, os, requests
from tabulator import Stream
from downloader import download_retry
from common import temp_file
load_dotenv(find_dotenv())

# import re
# caps = "([A-Z])"
# prefixes = "(Mr|St|Mrs|Ms|Dr)[.]"
# suffixes = "(Inc|Ltd|Jr|Sr|Co)"
# starters = "(Mr|Mrs|Ms|Dr|He\s|She\s|It\s|They\s|Their\s|Our\s|We\s|But\s|However\s|That\s|This\s|Wherever)"
# acronyms = "([A-Z][.][A-Z][.](?:[A-Z][.])?)"
# websites = "[.](com|net|org|io|gov)"
#
# def split_into_sentences(text):
#     text = " " + text + "  "
#     text = text.replace("\n"," ")
#     text = re.sub(prefixes,"\\1<prd>",text)
#     text = re.sub(websites,"<prd>\\1",text)
#     if "Ph.D" in text: text = text.replace("Ph.D.","Ph<prd>D<prd>")
#     text = re.sub("\s" + caps + "[.] "," \\1<prd> ",text)
#     text = re.sub(acronyms+" "+starters,"\\1<stop> \\2",text)
#     text = re.sub(caps + "[.]" + caps + "[.]" + caps + "[.]","\\1<prd>\\2<prd>\\3<prd>",text)
#     text = re.sub(caps + "[.]" + caps + "[.]","\\1<prd>\\2<prd>",text)
#     text = re.sub(" "+suffixes+"[.] "+starters," \\1<stop> \\2",text)
#     text = re.sub(" "+suffixes+"[.]"," \\1<prd>",text)
#     text = re.sub(" " + caps + "[.]"," \\1<prd>",text)
#     if "”" in text: text = text.replace(".”","”.")
#     if "\"" in text: text = text.replace(".\"","\".")
#     if "!" in text: text = text.replace("!\"","\"!")
#     if "?" in text: text = text.replace("?\"","\"?")
#     text = text.replace(".",".<stop>")
#     text = text.replace("?","?<stop>")
#     text = text.replace("!","!<stop>")
#     text = text.replace("<prd>",".")
#     sentences = text.split("<stop>")
#     sentences = sentences[:-1]
#     sentences = [s.strip() for s in sentences]
#     return sentences

def main():
    parameters, datapackage, resources = ingest()
    aggregations = {"stats": {}}
    session = requests.session()

    # def parse_sentence(meeting_id, order, i, sentence):
    #     for word in sentence.split(" "):
    #         word = word.strip().strip(".?!,")
    #         if len(word) > 6:
    #             yield {"meeting_id": meeting_id,
    #                    "part_order": order,
    #                    "sentence_order": i,
    #                    "word": word}

    def parse_protocol_part(meeting_id, order, part):
        # skip the first 10 parts - they are usually irrelevant
        if order > 10:
            header, body = part
            part_text = "{}\n{}".format(header, body)
            if len(part_text) > 30:
                yield {"part": part_text,
                       "order": order,
                       "meeting": meeting_id}

            # sentences = split_into_sentences(body)
            # for i, sentence in enumerate(sentences):
            #     if len(sentence) > 20:
            #         yield from parse_sentence(meeting_id, order, i, sentence)

    def parse_protocol_parts_file(filepath, meeting_row):
        i = 0
        with Stream(filepath, headers=1) as stream:
            for i, part_row in enumerate(stream, start=1):
                yield from parse_protocol_part(meeting_row["kns_session_id"], i, part_row)
        logging.info("num protocol parts = {}".format(i))

    def get_resource(resource, descriptor):
        for row in resource:
            if descriptor["name"] == "protocols":
                if row["parts_object_name"]:
                    url = "{}/{}".format("https://minio.oknesset.org/committees", row["parts_object_name"])
                    if parameters.get("protocols-cache-path"):
                        filepath = os.path.join(parameters["protocols-cache-path"], row["parts_object_name"])
                        if not os.path.exists(filepath):
                            logging.info("Downloading {} -> {}".format(url, filepath))
                            with open(filepath, "wb") as f:
                                f.write(download_retry(session, url))
                        yield from parse_protocol_parts_file(filepath, row)
                    else:
                        with temp_file() as filepath:
                            filepath = "{}.csv".format(filepath)
                            logging.info("Downloading {} -> {}".format(url, filepath))
                            with open(filepath, "wb") as f:
                                f.write(download_retry(session, url))
                            yield from parse_protocol_parts_file(filepath, row)
            else:
                yield row

    def get_resources():
        for resource, descriptor in zip(resources, datapackage["resources"]):
            yield get_resource(resource, descriptor)

    for descriptor in datapackage["resources"]:
        if descriptor["name"] == "committee_meeting_protocols_parsed":
            descriptor["name"] = "protocols"
            descriptor["path"] = "protocols.csv"
            # fields = [("meeting_id", "integer"),
            #           ("part_order", "integer"),
            #           ("sentence_order", "integer"),
            #           ("word", "string")]
            fields = [("part", "string", "text"),
                      ("order", "integer", "integer"),
                      ("meeting", "integer", "integer")]
            descriptor["schema"]["fields"] = [{"name": n, "type": t, "es:type": e} for n, t, e in fields]
            descriptor["schema"]["primaryKey"] = ["meeting", "order"]

    spew(datapackage, get_resources(), aggregations["stats"])


if __name__ == "__main__":
    main()
