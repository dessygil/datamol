from typing import Union
from typing import List

import re

import pandas as pd

from rdkit import Chem
import selfies as sf

import datamol as dm


def to_smiles(
    mol: Chem.Mol,
    canonical: bool = True,
    isomeric: bool = True,
    ordered: bool = False,
    explicit_bonds: bool = False,
    explicit_hs: bool = False,
    randomize: bool = False,
):
    """Convert a mol to a SMILES.

    Args:
        mol (Chem.Mol): a molecule.
        add_hs (bool, optional): Whether hydrogens should be added the SMILES. Default to False.
        canonical (bool, optional): if false no attempt will be made to canonicalize the molecule.
            Defaults to true.
        isomeric (bool, optional): whether to include information about stereochemistry in
            the SMILES. Defaults to True.
        ordered (bool, optional): whether to force reordering of the atoms
            first. Defaults to False.
        explicit_bonds (bool, optional): if true, all bond orders will be explicitly indicated in
            the output SMILES. Defaults to false.
        explicit_hs (bool, optional): if true, all H counts will be explicitly indicated in the
            output SMILES. Defaults to false.
        randomize (bool, optional): whether to randomize the generated smiles. Override `canonical`.
            Defaults to false.
    """
    if ordered:
        mol = dm.reorder_atoms(mol)

    if randomize:
        mol = dm.randomize_atoms(mol)
        canonical = False

    smiles = None
    try:
        smiles = Chem.MolToSmiles(
            mol,
            isomericSmiles=isomeric,
            canonical=canonical,
            allBondsExplicit=explicit_bonds,
            allHsExplicit=explicit_hs,
        )
    except:
        return None
    return smiles


def to_selfies(mol: Union[str, Chem.Mol]):
    """Convert a mol to SELFIES.

    Args:
        mol (Chem.Mol or str): a molecule or a SMILES.

    Returns:
        selfies (str): SELFIES string.
    """
    if mol is None:
        return None

    if isinstance(mol, Chem.Mol):
        mol = to_smiles(mol)

    return sf.encoder(mol)


def from_selfies(selfies: str, as_mol: bool = False):
    """Convert a SEFLIES to a smiles or a mol.

    Args:
        selfies (str): a selfies.
        as_mol (str, optional): whether to return a mol or a smiles.

    Returns:
        smiles or mol (str, Chem.Mol))
    """
    if selfies is None:
        return None

    smiles = sf.decoder(selfies)

    if as_mol and smiles is not None:
        return dm.to_mol(smiles)

    return smiles


def to_smarts(mol: Union[str, Chem.Mol], keep_hs: bool = True):
    """Convert a molecule to a smarts.

    Args:
        mol (Chem.Mol): a molecule.
        keep_hs (bool, optional): Whether to keep hydrogen. This will increase the count of H atoms
            for atoms with attached hydrogens to create a valid smarts.
            e.g. [H]-[CH2]-[*] -> [H]-[CH3]-[*]

    Returns:
        smarts of the molecule
    """

    if mol is None:
        return None

    if isinstance(mol, str):
        mol = dm.to_mol(mol)

    # Change the isotope to 42
    for atom in mol.GetAtoms():
        if keep_hs:
            s = sum(na.GetAtomicNum() == 1 for na in atom.GetNeighbors())
            if s:
                atom.SetNumExplicitHs(atom.GetTotalNumHs() + s)
        atom.SetIsotope(42)

    # Print out the smiles, all the atom attributes will be fully specified
    smarts = to_smiles(mol, isomeric=True, explicit_bonds=True)

    if smarts is None:
        return None

    # Remove the 42 isotope labels
    smarts = re.sub(r"\[42", "[", smarts)
    return smarts


def to_inchi(mol: Union[str, Chem.Mol]):
    """Convert a mol to Inchi.

    Args:
        mol (Union[str, Chem.Mol]): [description]
    """

    if mol is None:
        return None

    if isinstance(mol, str):
        mol = dm.to_mol(mol)

    return Chem.MolToInchi(mol)


def to_inchikey(mol: Union[str, Chem.Mol]):
    """Convert a mol to Inchi key.

    Args:
        mol (Union[str, Chem.Mol]): [description]
    """

    if mol is None:
        return None

    if isinstance(mol, str):
        mol = dm.to_mol(mol)

    return Chem.MolToInchiKey(mol)


def from_inchi(inchi: str, sanitize: bool = True, remove_hs: bool = True):
    """Convert a SEFLIES to a smiles or a mol.

    Args:
        inchi (str): a selfies.
        sanitize (bool, optional): do sanitize.
        remove_hs (bool, optional): do remove hs.

    Returns:
        smiles or mol (str, Chem.Mol))
    """
    if inchi is None:
        return None

    return Chem.MolFromInchi(inchi, sanitize=sanitize, removeHs=remove_hs)


def to_df(mols: List[Chem.Mol], smiles_column: str = "smiles"):
    """Convert a list of mols to a dataframe using each mol properties
    as a column.

    Args:
        mols (list of Chem.Mol
        smiles_column (str, optional): name of the SMILES column.
            Default to "smiles".
    """
    df = [mol.GetPropsAsDict() for mol in mols]
    df = pd.DataFrame(df)

    # Add the smiles column and move it to the first position
    smiles = [to_smiles(mol) for mol in mols]
    df[smiles_column] = smiles
    col = df.pop(smiles_column)
    df.insert(0, col.name, col)

    return df


def from_df(df: pd.DataFrame, smiles_column: str = "smiles"):
    """Convert a dataframe to a list of mols.

    Args:
        df (pd.dataframe): a dataframe.
        smiles_column (str, optional): Column name to use for smiles.
            Default to "smiles".
    """

    def _row_to_mol(row):
        mol = dm.to_mol(row[smiles_column])

        if mol is None:
            return None

        for k, v in row.to_dict().items():
            if isinstance(v, int):
                mol.SetIntProp(k, v)
            elif isinstance(v, float):
                mol.SetDoubleProp(k, v)
            elif isinstance(v, bool):
                mol.SetBoolProp(k, v)
            else:
                mol.SetProp(k, str(v))
        return mol

    return df.apply(_row_to_mol, axis=1).tolist()