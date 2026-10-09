# Dotfiles Manager

A small CLI dedicated to managing your dotfiles. Unlike tools that use symlinks, Doty uses hardlinks to keep your configs in sync without copying files. It also automatically initializes a Git repository for version control.

## Installation

```bash
# Clone the repo
git clone tbd
cd dotfiles-manager

# Install with pip
pip install .
```

## Usage

The CLI is called `doty`.

### Initialize a dotfiles repository

Create a dotfiles repository in your home directory:

```bash
doty init
```

### Link a config

Register a config in your dotfiles repository and its target location:

```bash
doty link path/in/dotfiles path/to/config/file
```

Run `doty update` to apply registered links.

### Unlink a config

Remove a registered link:

```bash
doty unlink path/to/config/file
```

### Add an existing config

Import an existing config into your dotfiles repository:

```bash
doty add path/to/config/file path/in/dotfiles
```

You can also use `--move` to move the file instead:

```bash
doty add --move ~/Downloads/epic-config.conf myWM/config.conf
```

### More

Run `doty --help` for a full list of commands and options.

## License

This project is licensed under TBD.
