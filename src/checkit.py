import sys
import click
import requests
from requests import RequestException
import settings
import json


@click.command()
@click.argument('manifest')
def main(manifest):

    sys.exit(checkit(manifest))


def checkit(manifest):
    """Simple DLCS other content tester"""
    print(f"checkit for manifest {manifest}")

    try:
        manifest_response = requests.get(manifest)
    except RequestException:
        click.echo(click.style('could not obtain manifest', bg="red", fg="black"))
        return 1
    manifest = json.loads(manifest_response.text)

    sequence_count = 0
    canvas_count = 0
    other_content_count = 0
    other_content_checked = 0
    other_content_success = 0
    failures = []

    services = manifest.get('service')
    if not services and settings.SERVICE_PROFILES:
        failures.append(f'no services on manifest')
    else:
        if not isinstance(services, list):
            services = [services]

        m_service_profiles = [oc.get('profile') for oc in services]
        for service_profile in settings.SERVICE_PROFILES:
            if service_profile not in m_service_profiles:
                failures.append(f'service with profile {service_profile} missing')
        for service in services:
            profile = service.get('profile')
            if profile in settings.SERVICE_PROFILES:
                at_id = service.get('@id')
                try:
                    # special case for search service, requires query param
                    if profile == 'http://iiif.io/api/search/0/search':
                        at_id += '?q=the'
                    response = requests.get(at_id)
                    if not response.ok:
                        failures.append(f"status code {response.status_code} for service {at_id}")
                except RequestException:
                    failures.append(f"could not obtain service {at_id}")

    sequences = manifest.get('sequences')
    if not sequences:
        failures.append(f"no sequences present")
    else:
        for sequence in sequences:
            sequence_count += 1
            canvases = sequence.get('canvases')
            if not canvases:
                sequence_id = sequence.get('@id')
                failures.append(f'sequence {sequence_id} has no canvases')
            else:
                for canvas in canvases:
                    canvas_count += 1
                    canvas_id = canvas.get('@id')
                    other_contents = canvas.get('otherContent')
                    if not other_contents:
                        failures.append(f'canvas {canvas_id} has no other contents')
                    else:
                        oc_labels = [oc.get('label') for oc in other_contents]
                        for label in settings.REQUIRED_OTHER_CONTENT:
                            if label not in oc_labels:
                                failures.append(f'other content with label {label} missing from {canvas_id}')
                        for other_content in other_contents:
                            other_content_count += 1
                            label = other_content.get('label')
                            if label in settings.OTHER_CONTENT_LABELS:
                                at_id = other_content.get('@id')
                                try:
                                    response = requests.get(at_id)
                                    if response.ok:
                                        other_content_success += 1
                                    else:
                                        failures.append(f"status code {response.status_code} for canvas {at_id}")
                                except RequestException:
                                    failures.append(f"could not obtain {at_id}")

                                other_content_checked += 1

    exit_code = 0
    if not failures:
        click.echo(click.style('All successful', fg='green'))
    else:
        click.echo(click.style(f'There were {len(failures)} failures:', bg="red", fg="black"))
        for count, failure in enumerate(failures):
            click.echo(click.style(str(count + 1) + '>', fg='yellow') + failure)
        exit_code = 1
    click.echo(f'\ntotal sequence count: {sequence_count}')
    click.echo(f'total canvas count: {canvas_count}')
    click.echo(f'total other content count: {other_content_count}')
    click.echo(f'other content checked: {other_content_checked}')
    click.echo(f'other content success: {other_content_success}')

    exit(exit_code)


if __name__ == '__main__':

    main()
