(install)=
# Installing CSM

## Install CSM via PyPI

If you just want to use CSM and aren't developing new models, you can install it from PyPI using pip:

```bash
pip install # TODO
```

## Installing from source

If you want to develop new models or contribute to CSM, you can install it from source.

1. Using Git, navigate to a local target directory and clone repository:

    ```bash
    git clone https://github.com/NLRWindSystems/CSM.git
    ```

2. Navigate to `CSM`

    ```bash
    cd CSM
    ```

3. Create a new virtual environment and change to it. Using Conda Python 3.11 (choose your favorite
   supported version) and naming it "csm" (choose your desired name):

    ```bash
    conda create --name csm python=3.11 -y
    conda activate csm
    ```

4. Install CSM and its dependencies:

   - If you want to just use CSM:

       ```bash
       pip install .
       ```

    - If you also want development dependencies and documentation build tools:

       ```bash
       pip install -e ".[develop]"
       pre-commit install
       ```

## Developer Installation

Please see the [Contributor's Guide](#contributor-guide) for notes on installation steps and general
notes geared towards maintainers and contributors of the project.
