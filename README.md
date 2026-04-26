# MCU-Development-Assistant
Driver development using LLM

MiniConda installation: download path
https://www.anaconda.com/download/success
Complete installation and check version number.
Win+R cmd --> conda --version
conda xx.x.x should pop up.
**Step 1:**

commands reference for conda (https://docs.conda.io/projects/conda/en/stable/commands/index.html).
create a project environment.
conda create -n mcu_assistant python=3.11
it will ask for terms of service accept press (a) for all the three.
Do you accept the Terms of Service (ToS) for https://repo.anaconda.com/pkgs/main? [(a)ccept/(r)eject/(v)iew]: a
Do you accept the Terms of Service (ToS) for https://repo.anaconda.com/pkgs/r? [(a)ccept/(r)eject/(v)iew]: a
Do you accept the Terms of Service (ToS) for https://repo.anaconda.com/pkgs/msys2? [(a)ccept/(r)eject/(v)iew]: a

it will install below packages (it may vary based on version and other files installed earlier).
The following packages will be downloaded:

    package                    |            build
    ---------------------------|-----------------
    bzip2-1.0.8                |       h2bbff1b_6          90 KB
    ca-certificates-2026.3.19  |       haa95532_0         126 KB
    libexpat-2.7.5             |       hd7fb8db_0         120 KB
    libffi-3.4.4               |       hd77b12b_1         122 KB
    libzlib-1.3.1              |       h1c6eee0_1          62 KB
    openssl-3.5.6              |       hbb43b14_0         8.9 MB
    packaging-26.0             |  py311haa95532_0         197 KB
    pip-26.0.1                 |     pyhc872135_1         1.1 MB
    python-3.11.15             |       h1044e36_0        17.7 MB
    setuptools-82.0.1          |  py311haa95532_0         1.6 MB
    sqlite-3.51.2              |       hee5a0db_0         917 KB
    tk-8.6.15                  |       hf199647_0         3.5 MB
    tzdata-2026a               |       he532380_0         117 KB
    ucrt-10.0.22621.0          |       haa95532_0         620 KB
    vc-14.3                    |      h2df5915_10          19 KB
    vc14_runtime-14.44.35208   |      h4927774_10         825 KB
    vs2015_runtime-14.44.35208 |      ha6b5a95_10          19 KB
    wheel-0.46.3               |  py311haa95532_0          95 KB
    xz-5.8.2                   |       h53af0af_0         265 KB
    zlib-1.3.1                 |       h1c6eee0_1         104 KB
    ------------------------------------------------------------
                                           Total:        36.4 MB
type y , it will install all the packages.





                                           
