<!--
IMPORTANT NOTES

1. Pull requests will be rejected if the template is incorrectly filled out or incomplete.

2. Use GH flavored markdown when writing your description:
   https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax

3. If all boxes in the PR Checklist cannot be checked, this PR should be marked as a draft.

4. DO NOT DELTE ANYTHING FROM THIS TEMPLATE. If a section does not apply to you, simply write
   "N/A" in the description.

5. Code snippets to highlight new, modified, or problematic functionality are highly encouraged,
   though not required. Be sure to use proper code higlighting as demonstrated below.

   ```python
    def a_func():
        return 1

    a = 1
    b = a_func()
    print(a + b)
    ```
-->

<!--The title should clearly define your contribution succinctly.-->
# Add meaningful title here

<!-- Describe your contribution here. Please include any code snippets or examples in this section. -->


## PR Checklist

<!--Tick these boxes if they are complete, or format them as "[x]" for the markdown to render. -->
- [ ] `CHANGELOG.md` has been updated to describe the changes made in this PR
- [ ] Documentation
  - [ ] Docstrings are up-to-date
  - [ ] Related `docs/` files are up-to-date, or added when necessary
  - [ ] Documentation has been rebuilt successfully
  - [ ] Examples have been updated
- [ ] Tests pass (If not, and this is expected, please elaborate in the tests section)
- [ ] PR description thoroughly describes the new feature, bug fix, etc.


<!-- Use this subsection to tick off completed requirements for a new model contribution -->
### New Model Checklist

<!--
For reference on how to setup a new model and its respective documentation, please
review the 2020 and 2021 models and their documentation. Please review
https://nlrwindsystems.github.io/CSM/intro/contributing.html#new-models and
https://nlrwindsystems.github.io/CSM/user_guide/new_models.html for more information on creating
new models.

NOTE: PRs will be rejected if new model submissions are unable to satisfy all of the following
criteria.
-->
- [ ] `parameter_map` has been updated to reflect the required variables for each calculation
- [ ] New tests created
  - [ ] Unit tests
  - [ ] Regression tests
- [ ] Model docstrings
  - [ ] New default values are listed
  - [ ] New and deprecated scaling models are highlighted in the description
  - [ ] New scaling model methods adhere to the existing format for model equations and required inputs
- [ ] Model documentation
  - [ ] New documentation page has been added to `docs/api/models/`
    - [ ] `autoclass` is setup similar to existing models to control displayed elements
    - [ ] Updated scaling relationships have a dedicated subsection
    - [ ] All calculations are correctly referenced in the reference tables
          (these can be copied and modified from an existing model or from `_base_calculations.md`
          or `_shared_functionality.md`)
  - [ ] The new documentation page is indexed appropriately in `docs/api/index.md`

## Related issues

<!--If one exists, link to a related GitHub Issue.-->


## Impacted areas of the software

<!--
Replace the below example with any added or modified files, and briefly describe what has been changed or added, and why.
-->
- `path/to/file.extension`
  - `method1`: What and why something was changed in one sentence or less.

## Additional supporting information

<!--Fill out at least the versions listed below and those of any packages that may be related.-->
Python version: 3.x
CSM version (`CSM.__version__`): 0.x

<!--Add any other context about the problem here, or testing/documentation issues.-->
