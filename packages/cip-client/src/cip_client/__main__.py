from cip_client.cli import CipClientCli
import fire


def main():
    fire.Fire(CipClientCli)


if __name__ == "__main__":
    main()