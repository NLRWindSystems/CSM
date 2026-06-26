(contributor-guide)=
# Contributor's Guide

We welcome contributions in the form of bug reports, bug fixes, improvements to the documentation,
ideas for enhancements (or the enhancements themselves!).

You can find a [list of current issues](https://github.com/NLRWindSystems/CSM/issues) in the
project's GitHub repo. Feel free to tackle any existing bugs or enhancement ideas by submitting a
[pull request](https://github.com/NLRWindSystems/CSM/pulls).

(developer-install)=
## Installing CSM for Developers

Please see the [Installation Guide](#install) for how to set up an environment and install CSM.

Developers should add install using `pip install -e .[develop]` after creating a CSM environment to
ensure the documentation, testing, and linting can be done without any additional installation steps.

Please be sure to also install the pre-commit hooks if contributing code back to the main
repository via the following. This enables a series of automated formatting and code linting
(style and correctness checking) to ensure the code is stylistically consistent.

```bash
pre-commit install
```

If a check (or multiple) fails (commit is blocked), and reformatting was done, then restage
(`git add`) your files and commit them again to see if all issues were resolved without user
intervention. If changes are required follow the suggested fix, or resolve the stated
issue(s). Restaging and committing may take multiple attempts steps if errors are unaddressed
or insufficiently addressed. Please see [pre-commit](https://pre-commit.com/),
[ruff](https://docs.astral.sh/ruff/), or [isort](https://pycqa.github.io/isort/) for more
information.

## Bug Reports

* Please include a short (but detailed) Python snippet or explanation for reproducing the problem.
  Be sure to attach or include a link to any input files that will be needed to reproduce the error.
* Explain the behavior you expected, and how what you got differed.

## Submitting Code (Through Pull Requests)

1. Fork the repository to your personal GitHub Account.
2. Clone your fork, replacing "AccountName" with your user name.

   ```bash
   git clone https://github.com/AccountName/CSM.git
   ```

3. For general development, create a branch off of `develop`, for a hot fix/patch, create a branch off
   of `main`. Use either example as a base. In general it's common to indicate the type of
   development with text before the slash such as `fix/`, `patch/`, `feature/`, `enhancement/`,
   etc., followed by a short dash-separate description of the contribution, such as
   `enhancement/pandas-v3-upgrade`. See below for an example of creating a new branch based off
   either `develop` or `main`.

   ```bash
   git checkout develop
   git checkout -b feature/new-model
   ```

   Or

   ```bash
   git checkout main
   git checkout -b patch/fix-issue
   ```

4. Commit and push your changes in stages to track the various states of your development, though
   less ideally, you may do this step all at once when development is complete.

   ```bash
   git add <files-that-were-updated>
   git commit -m "short description of changes"
   git push
   ```

5. Open a pull request. The remainder of this section will walk through the requirements that should
   be met prior to submitting a pull request to the `develop` or `main` branch of the repository.

:::{important}
Pull requests should be submitted to the `develop` branch unless a new release is being created. If
so, please also read the [release guide](#release-process).
:::

* Changes should be pass the linting and autoformatting checks provided through `pre-commit`.
  If they do not, the PR's CI pipeline will fail and will block the acceptance of your
  contributions until they pass. If your commit fails, then check the `pre-commit` logs to see
  if any fixes were automatically applied or if manual changes are required. Once the changes are
  made, simply reattempt to add and commit your files.
* Keep style fixes to a separate commit to make your pull request more readable.
* Docstrings are required and should follow the
  [Google style](https://www.sphinx-doc.org/en/master/usage/extensions/example_google.html).
* When you start working on a pull request, start by creating a new branch pointing at the latest
  commit on [develop](https://github.com/NLRWindSystems/CSM/tree/develop) based on your own fork
  (i.e., replace "NLRWindSystems" with your GitHub username).
* The CSM copyright policy is detailed in the
  [`LICENSE`](https://github.com/NLRWindSystems/CSM/blob/main/LICENSE).
* Build the docs locally, check that the build everything is in good order, and links work.

### Merging Pull Requests

Assuming the PR has been successfully reviewed, please read on.

For any development branch (e.g., `feature/my-contribution` -> `develop` or `fix/important-bug` ->
`main`), always use the "squash and merge" method for merging PRs (use merge button's drop down
menu).

For the standard release process (i.e., `develop` -> `main`), always use the standard merge process
(create a merge commit in the merge button's drop down menu).

## Documentation

When contributing new features or fixing existing capabilities, be sure to add and/or update the
docstrings as needed to ensure the documentation site stays up to date with the latest changes.
Please also update any relevant guides or examples in the documentation if functionality has
changed, or if there is new functionality that should be highlighted.

### Building the Documentation Site

Once the `develop` extras are installed, and your CSM environment is activated, the documentation can
be built using the following two procedures.

### Generate the Local Documentation Site for Inspection

```bash
jupyter-book build docs/
```

For more information on the build process in Jupyter Book, please check:
https://jupyterbook.org/v1/basics/build.html. For more general details, please visit
https://jupyterbook.org/v1/intro.html.

### Viewing the Locally Built Documentation

In addition to building the documentation, be sure to check the results by opening the following
path in your browser: `file:///<path-to-CSM>/CSM/docs/_build/html/index.html`.

```{note}
If the browser appears to be out of date from what you expected to be built, please try reloading
the page a few times. If that doesn't work, then:

1. Close the documentation tab
2. Clear your browser's cache
3. Rebuild the docs using [prior to a PR section](#prior-to-a-pull-request)
4. Open the page again.
```

## Release Process

### Standard

Most contributions will be into the `develop` branch, and once the threshold for a release has been
met the following steps should be taken to create a new release

1. On `develop`, bump the version appropriately, see the
   [semantic versioning guidelines](https://semver.org/) for details.
   * Semantic Versioning follows a MAJOR.MINOR.PATCH versioning pattern, and new functionality
     should get a minor release, and fixes/minor updates should get a patch release.
2. Update the `## Unreleased` title to the new version and release date.
3. Open a pull request from `develop` into `main`.
4. When all CI tests pass, and the PR has been approved, merge the PR into main.
5. Pull the latest changes from GitHub into the local copy of the main branch.
6. Tag the latest commit to match the version bump in step 1 (replace "v1.2.3" in all instances
   below), and push it to the repository.

   ```bash
   git tag -a v1.2.3 -m "v1.2.3 release"
   git push origin v1.2.3
   ```

7. Check that the
   [Test PyPI GitHub Action](https://github.com/NLRWindSystems/CSM/actions/workflows/publish_to_test_pypi.yml)
   has run successfully.
   1. If the action failed, identify and fix the issue, then
   2. delete the local and remote tag using the following (replace "v1.2.3" in all instances just like
      in step 6):

      ```bash
      git tag -d v1.2.3
      git push --delete origin v1.2.3
      ```

   3. Start back at step 1.
8. When the Test PyPI Action has successfully run,
   [create a new release](https://github.com/NLRWindSystems/CSM/releases/new) using the tag created in
   step 6.

### Patches

Any pull requests directly into the main branch that alter the CSM model (excludes anything
in `docs/`, or outside of `csm/` and `tests/`), should be sure to follow the instructions
below:

1. All CI tests pass and the patch version has been bumped according to the
   [semantic versioning guidelines](https://semver.org/).
2. Follow steps 2 through 8 above.
3. Merge the NLRWindSystems main branch back into the `develop` branch and push the changes.
