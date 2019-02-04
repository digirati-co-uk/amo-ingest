import click
import requests
import settings
import json
import sys
from time import time, sleep
from jwt_client import JWTClient


@click.command()
@click.option("-s", help="success criteria file")
@click.argument("template")
def main(s, template):
    """Simple DLCS pipeline tester"""

    exit_code, manifest = pokeit(s, template)
    sys.exit(exit_code)


def pokeit(s, template):

    success_criteria = []
    check_success = False

    if s:
        with open(s) as f:
            success_criteria = json.load(f)
            check_success = True

    manifest_id, manifest = get_manifest(template)
    click.echo(
        click.style("Manifest being created: ", fg="green") + click.style(manifest_id, fg="yellow")
    )
    add_to_presley(manifest)
    click.echo(
        click.style("Manifest posted to Presley as: ", fg="green") + click.style(manifest_id, fg="yellow")
    )
    return check_giles(manifest_id, check_success, success_criteria), manifest_id


def check_giles(manifest_id, check_success, success_criteria):

    received = set()
    session = None
    session_attempts = 0
    start_time = int(round(time()))

    while True:  # TODO : define end criteria

        if session is None:

            # we don't yet know the session for this manifest
            session = check_messages_for_session(manifest_id)
            if session is None:
                session_attempts += 1
                if session_attempts % 5 == 0:
                    # every 5 attempts
                    click.echo(
                        click.style(
                            "Still did not find session after {seconds} seconds".format(
                                seconds=settings.UPDATE_INTERVAL * session_attempts
                            ),
                            fg="red",
                        )
                    )
            else:
                click.echo(
                    click.style("Session identified as: ", fg="green")
                    + click.style(session, fg="yellow")
                )

        if session:
            messages = get_session_messages(session)
            for message in messages:
                message_id = message["message_id"]
                if message_id not in received:
                    process_message(message)
                    received.add(message_id)
                    if check_success:
                        successful = check_message(message, success_criteria)
                        if successful:
                            click.echo(click.style("SUCCESS", bg="green", fg="black"))
                            return 0

        if check_success and success_criteria.get("timeout") < int(round(time()) - start_time):
            click.echo(
                click.style("FAILURE", bg="red", fg="black") + click.style(" (timeout)", fg="green")
            )
            return 0
        sleep(settings.UPDATE_INTERVAL)


def check_message(message, success_criteria):

    for criteria in [c for c in success_criteria.get("required") if not c.get("met")]:
        properties_met = True
        for criteria_property in criteria:
            if not message.get(criteria_property) == criteria.get(criteria_property):
                properties_met = False
                break
        if properties_met:
            criteria["met"] = True

    if not any([c for c in success_criteria.get("required") if not c.get("met")]):
        return True
    return False


def check_messages_for_session(manifest_id):

    messages = get_presley_add_messages(manifest_id)
    if len(messages) > 0:
        message = messages[0]
        if "session" in message:
            return message["session"]
    return None


def get_presley_add_messages(manifest_id):

    query = {
        "size": 1000,
        "sort": [{"timestamp": {"order": "desc"}}],
        "query": {
            "bool": {
                "must": [
                    {"range": {"timestamp": {"gte": "now-5m"}}},
                    {
                        "bool": {
                            "should": [
                                {"term": {"message_type.keyword": "Presley_Manifest_Updated"}},
                                {"term": {"message_type.keyword": "Presley_Manifest_Added"}},
                            ]
                        }
                    },
                    {"term": {"manifest_id.keyword": manifest_id}},
                ]
            }
        },
    }

    return es_query(query)


def get_session_messages(session):

    query = {
        "size": 1000,
        "sort": [{"timestamp": {"order": "asc"}}],
        "query": {"term": {"session.keyword": session}},
    }
    return es_query(query)


def es_query(query):

    resp = requests.post(settings.ES_HOST + "/" + settings.ES_INDEX + "/_search", json=query)
    return [
        message["_source"]
        for message in resp.json()["hits"]["hits"]
        if "message_id" in message["_source"]
    ]


def process_message(message):

    if (
        message.get("message_type") == "Presley_Manifest_Added"
        or message.get("message_type") == "Presley_Manifest_Updated"
    ):
        manifest_id = message.get("manifest_id")
        click.echo(
            click.style("Manifest ", fg="green")
            + click.style(manifest_id, fg="blue")
            + click.style(" added to Presley", fg="green")
        )

    elif message.get("message_type") == "Destiny_Manifest_Added":
        manifest_id = message.get("manifest_id")
        click.echo(
            click.style("Manifest ", fg="green")
            + click.style(manifest_id, fg="blue")
            + click.style(" added to Destiny", fg="green")
        )

    elif message.get("message_type") == "Canvas_Processed":
        canvas_id = message.get("canvas_id")
        resolution = message.get("resolution")
        process = message.get("process")
        click.echo(
            click.style("Canvas ", fg="green")
            + click.style(canvas_id, fg="blue")
            + click.style(" processed by ", fg="green")
            + click.style(process, fg="red")
            + " "
            + click.style(
                resolution.upper(), fg="black", bg="green" if resolution == "success" else "red"
            )
        )

    elif message.get("message_type") == "Manifest_Processed":
        manifest_id = message.get("manifest_id")
        resolution = message.get("resolution")
        process = message.get("process")
        click.echo(
            click.style("Manifest ", fg="green")
            + click.style(manifest_id, fg="blue")
            + click.style(" processed by ", fg="green")
            + click.style(process, fg="red")
            + " "
            + click.style(
                resolution.upper(), fg="black", bg="green" if resolution == "success" else "red"
            )
        )


def get_manifest(template):
    if template.startswith("http"):
        response = requests.get(template)
        manifest = response.text
    else:
        with open(template) as fin:
            manifest = fin.read()

    manifest_obj = json.loads(manifest)
    manifest_id = manifest_obj.get("@id")
    return manifest_id, manifest


def add_to_presley(manifest):

    jwt = JWTClient(settings.PRESLEY_BASE + "/login", settings.PRESLEY_USER, settings.PRESLEY_PASS)
    resp = jwt.post(
        settings.PRESLEY_BASE + "/customer/manifest/add",
        data=manifest.encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    print("Presley response: ", resp.status_code)
    resp.raise_for_status()


if __name__ == "__main__":

    main()
