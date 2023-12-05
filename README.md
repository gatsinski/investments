# investments

A simple and easy to use investments tracker.

## Setup

### Prerequisites

The following requirements need to be satisfied to setup the project.

1. [**Python**](https://www.python.org/) - While the project may work with any Python version above 3.5 it is actively developed using 3.10 and it is the officially supported version. Use any other Python version at your own risk.
1. [**Pipenv**](https://github.com/pypa/pipenv) - Used for installing backend dependencies. The latest version is the one usually used for development but the tool is stable and most versions should work flawlessly.

### Installation steps

1. Navigate to the project's root directory.
1. Execute `pipenv install` to install the backend dependencies.
1. Type `pipenv run migrate` to apply all database migrations. Currently, the default database is SQLite. Edit the settings.py file if you want to use MySQL/MariaDB or PostgreSQL. Read the official Django [documentation](https://docs.djangoproject.com/en/4.2/ref/databases/) to learn more.

### Development

Start the development server using `pipenv run server` and navigate to http://localhost:8000 in your browser.
If you need admin access you can create a privileged user by executing `pipenv run manage createsuperuser`.
If you need to execute something else within the project's environment, you can enter the environment using `pipenv shell`.
