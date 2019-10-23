"""Wildcard labels."""
from wcmatch import glob
from gidgethub import sansio


async def get_flags(config):
    """Get glob flags."""

    flags = glob.GLOBSTAR | glob.DOTGLOB | glob.NEGATE | glob.SPLIT | glob.NEGATEALL
    if config.get('brace_expansion', False):
        flags |= glob.BRACE
    if config.get('extended_glob', False):
        flags |= glob.EXTGLOB | glob.MINUSNEGATE
    if config.get('case_insensitive', False):
        flags |= glob.IGNORECASE
    return flags


async def wildcard_labels(event, gh, config):
    """Label issues by files that are changed."""

    sha = event.data['pull_request']['head']['sha']
    flags = await get_flags(config)
    files = await get_changed_files(event, gh, config)
    add, remove = await get_labels(files, flags)
    await update_issue_labels(event, gh, add, remove)


async def get_changed_files(event, gh, files):
    """Get changed files."""

    files = []
    compare = await gh.getitem(
        event.data['repository']['compare_url'].format(
            base=event.data['pull_request']['base']['label'],
            head=event.data['pull_request']['head']['label']
        ),
        accept=sansio.accept_format(version="v3")
    )
    for file in compare['files']:
        files.append(file['filename'])
    return files


async def get_labels(files, flags):
    """Sync labels."""

    add_labels = {}
    for file in files:
        for label in self.labels:
            names = label['labels']
            lows = [n.lower() for n in names]
            match = False
            for pattern in label['patterns']:
                if glob.globmatch(file, pattern, flags=self.flags):
                    match = True
                    break
            if match:
                for index, low in enumerate(lows):
                    if low not in add_labels:
                        add_labels[low] = names[index]
                break

    remove_labels = {}
    for label in self.labels:
        names = label['labels']
        lows = [n.lower() for n in names]
        for index, low in enumerate(lows):
            if low not in add_labels and low not in remove_labels:
                remove_labels[low] = names[index]

    return add_labels, remove_labels


def update_issue_labels(event, gh, add_labels, remove_labels):
    """Update issue labels."""

    labels = []
    url = event.data['pull_request']['issue_url'] + '/labels'
    accept = 'application/vnd.github.symmetra-preview+json'
    changed = False
    async for label in gh.getiter(url, accept=accept):
        name = label['name']
        low = name.lower()
        if low not in remove_labels:
            labels.append(name)
            if low in add_labels:
                del add_labels[low]
        else:
            changed = True

    new_labels = [label for label in add_labels.values()]
    if new_labels:
        changed = True
        labels.extend(new_labels)
    if changed:
        await gh.post(url, {'labels': labels}, accept=accept)
