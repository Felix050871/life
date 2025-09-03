{ pkgs }: {
  deps = [
    pkgs.postgresql_16
    pkgs.openssh
    pkgs.unzip
    pkgs.zip
    pkgs.openssl
  ];
}