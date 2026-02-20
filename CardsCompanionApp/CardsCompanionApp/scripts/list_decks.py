import json
import urllib.request

ANKI_URL = "http://127.0.0.1:8765"


def request(action, **params):
    req = urllib.request.Request(
        ANKI_URL,
        json.dumps({
            "action": action,
            "version": 6,
            "params": params
        }).encode("utf-8")
    )
    return json.load(urllib.request.urlopen(req))


def main():
    try:
        resp = request("deckNames")
        # Structure attendue : {"result": [...], "error": None}
        if resp.get("error") is not None:
            print("ERROR:" + str(resp["error"]))
            return

        decks = resp.get("result", [])
        for name in decks:
            print(name)
    except Exception as e:
        # On encode l’erreur sur une seule ligne, préfixée par ERROR:
        print("ERROR:" + repr(e))


if __name__ == "__main__":
    main()
