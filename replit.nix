{ pkgs }: {
  deps = [
    pkgs.openssh
    pkgs.unzip
    pkgs.zip
    pkgs.postgresql
    pkgs.openssl
  ];
}