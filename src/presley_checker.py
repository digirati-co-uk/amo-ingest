import requests
import os


def check_manifest(manifest_uri):
    """
    Check if an AMO manifest exists in the DLCS.

    :param manifest_uri:
    :return:
    """
    if manifest_uri:
        r = requests.get("https://presley.dlc-services.africamediaonline.com/iiif/customer/manifest?manifest_id="
                         + manifest_uri)
        print("Checking: ", "https://presley.dlc-services.africamediaonline.com/iiif/customer/manifest?manifest_id="
                         + manifest_uri)
        if r.status_code == requests.codes.ok:
            return manifest_uri, True
        else:
            return manifest_uri, False
    else:
        return manifest_uri, None


def check_all(text_file):
    """
    Check all manifests in a text file.

    :param text_file:
    :return:
    """
    if os.path.exists(text_file):
        with open(text_file, "r") as f:
            txt = f.readlines()
            for t in txt:
                r = requests.get(t.strip())
                if r.status_code == requests.codes.ok:
                    print("Checking: ", t.strip())
                    print("ID: ", r.json().get("@id"))
                    print("In DLCS: ", check_manifest(r.json().get("@id")))
                    print("\n")


# print(check_manifest("http://f9e1ea2c-20b1-11e9-ba92-d9b3dc251f06"))

check_all('../manifests_pdfs_ststithians.txt')